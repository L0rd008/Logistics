"""
Implementation of route optimization using Google OR-Tools.

This module provides classes and functions for solving Vehicle Routing Problems
(VRP) using Google's OR-Tools library.
"""
from typing import Dict, List, Tuple, Optional, Any
import logging
import numpy as np
from dataclasses import dataclass, field
from ortools.constraint_solver import routing_enums_pb2
from ortools.constraint_solver import pywrapcp

from route_optimizer.core.distance_matrix import Location

# Set up logging
logger = logging.getLogger(__name__)


@dataclass
class Vehicle:
    """Class representing a vehicle with capacity and other constraints."""
    id: str
    capacity: float
    start_location_id: str  # Where the vehicle starts from
    end_location_id: Optional[str] = None  # Where the vehicle must end (if different)
    cost_per_km: float = 1.0  # Cost per kilometer
    fixed_cost: float = 0.0   # Fixed cost for using this vehicle
    max_distance: Optional[float] = None  # Maximum distance the vehicle can travel
    max_stops: Optional[int] = None  # Maximum number of stops
    available: bool = True
    skills: List[str] = field(default_factory=list)  # Skills/capabilities this vehicle has


@dataclass
class Delivery:
    """Class representing a delivery with demand and constraints."""
    id: str
    location_id: str
    demand: float  # Demand quantity
    priority: int = 1  # 1 = normal, higher values = higher priority
    required_skills: List[str] = field(default_factory=list)  # Required skills
    is_pickup: bool = False  # True for pickup, False for delivery


class ORToolsVRPSolver:
    """
    Vehicle Routing Problem solver using Google OR-Tools.
    """

    def __init__(self, time_limit_seconds: int = 30):
        """
        Initialize the VRP solver.

        Args:
            time_limit_seconds: Time limit for the solver in seconds.
        """
        self.time_limit_seconds = time_limit_seconds

    def solve(
        self,
        distance_matrix: np.ndarray,
        location_ids: List[str],
        vehicles: List[Vehicle],
        deliveries: List[Delivery],
        depot_index: int = 0
    ) -> Dict[str, Any]:
        """
        Solve the Vehicle Routing Problem.

        Args:
            distance_matrix: 2D numpy array of distances between locations.
            location_ids: List of location IDs corresponding to matrix indices.
            vehicles: List of Vehicle objects.
            deliveries: List of Delivery objects.
            depot_index: Index of the depot location in the distance matrix.

        Returns:
            Dictionary containing the solution details:
            {
                'status': 'success' or 'failed',
                'routes': List of routes, where each route is a list of location indices,
                'total_distance': Total distance of all routes,
                'assigned_vehicles': Dict mapping vehicle IDs to route indices,
                'unassigned_deliveries': List of unassigned delivery IDs
            }
        """
        # Create the routing index manager
        num_locations = len(location_ids)
        num_vehicles = len(vehicles)
        
        # Create location_id to index mapping
        location_id_to_index = {loc_id: idx for idx, loc_id in enumerate(location_ids)}
        
        # Map vehicle start/end locations to indices
        starts = []
        ends = []
        
        for vehicle in vehicles:
            try:
                start_idx = location_id_to_index[vehicle.start_location_id]
                # If end location not specified, use the start location
                end_idx = location_id_to_index.get(
                    vehicle.end_location_id or vehicle.start_location_id,
                    start_idx
                )
                starts.append(start_idx)
                ends.append(end_idx)
            except KeyError as e:
                logger.error(f"Vehicle location not found in locations: {e}")
                return {
                    'status': 'failed',
                    'error': f"Vehicle location not found: {e}"
                }
        
        manager = pywrapcp.RoutingIndexManager(
            num_locations, 
            num_vehicles,
            starts,
            ends
        )
        
        # Create Routing Model
        routing = pywrapcp.RoutingModel(manager)
        
        # Create and register a transit callback
        def distance_callback(from_index, to_index):
            """Returns the distance between the two nodes."""
            # Convert from routing variable Index to distance matrix NodeIndex
            from_node = manager.IndexToNode(from_index)
            to_node = manager.IndexToNode(to_index)
            return int(distance_matrix[from_node][to_node] * 1000)  # Convert to int for OR-Tools
        
        transit_callback_index = routing.RegisterTransitCallback(distance_callback)
        
        # Define cost of each arc
        routing.SetArcCostEvaluatorOfAllVehicles(transit_callback_index)
        
        # Add Capacity constraint
        def demand_callback(from_index):
            """Returns the demand of the node."""
            # Convert from routing variable Index to demands NodeIndex
            from_node = manager.IndexToNode(from_index)
            # Get the location ID for this node
            location_id = location_ids[from_node]
            
            # Find all deliveries for this location
            total_demand = 0
            for delivery in deliveries:
                if delivery.location_id == location_id:
                    if delivery.is_pickup:
                        # For pickups, demand is negative (adds capacity)
                        total_demand -= delivery.demand
                    else:
                        # For deliveries, demand is positive (uses capacity)
                        total_demand += delivery.demand
            
            return int(total_demand * 100)  # Convert to int for OR-Tools
        
        demand_callback_index = routing.RegisterUnaryTransitCallback(demand_callback)
        
        # Set vehicle capacities
        for i, vehicle in enumerate(vehicles):
            routing.AddDimensionWithVehicleCapacity(
                demand_callback_index,
                0,  # null capacity slack
                [int(v.capacity * 100) for v in vehicles],  # vehicle maximum capacities
                True,  # start cumul to zero
                'Capacity'
            )
        
        # Setting first solution heuristic
        search_parameters = pywrapcp.DefaultRoutingSearchParameters()
        search_parameters.first_solution_strategy = (
            routing_enums_pb2.FirstSolutionStrategy.PATH_CHEAPEST_ARC
        )
        search_parameters.local_search_metaheuristic = (
            routing_enums_pb2.LocalSearchMetaheuristic.GUIDED_LOCAL_SEARCH
        )
        search_parameters.time_limit.seconds = self.time_limit_seconds
        
        # Solve the problem
        solution = routing.SolveWithParameters(search_parameters)
        
        # Return the solution
        if solution:
            routes = []
            assigned_vehicles = {}
            total_distance = 0
            
            for vehicle_idx in range(num_vehicles):
                route = []
                index = routing.Start(vehicle_idx)
                
                while not routing.IsEnd(index):
                    node_idx = manager.IndexToNode(index)
                    route.append(location_ids[node_idx])
                    previous_index = index
                    index = solution.Value(routing.NextVar(index))
                    total_distance += routing.GetArcCostForVehicle(
                        previous_index, index, vehicle_idx
                    ) / 1000  # Convert back from int
                
                # Add the end location
                node_idx = manager.IndexToNode(index)
                route.append(location_ids[node_idx])
                
                if route:  # If the route is not empty
                    routes.append(route)
                    assigned_vehicles[vehicles[vehicle_idx].id] = len(routes) - 1
            
            # Check for unassigned deliveries
            unassigned_deliveries = []
            delivery_locations = set()
            
            # Collect all locations in the routes
            for route in routes:
                delivery_locations.update(route)
            
            # Find deliveries that weren't assigned
            for delivery in deliveries:
                if delivery.location_id not in delivery_locations:
                    unassigned_deliveries.append(delivery.id)
            
            return {
                'status': 'success',
                'routes': routes,
                'total_distance': total_distance,
                'assigned_vehicles': assigned_vehicles,
                'unassigned_deliveries': unassigned_deliveries
            }
        else:
            return {
                'status': 'failed',
                'error': 'No solution found!'
            }

    def solve_with_time_windows(
        self,
        distance_matrix: np.ndarray,
        location_ids: List[str],
        vehicles: List[Vehicle],
        deliveries: List[Delivery],
        locations: List[Location],
        depot_index: int = 0,
        speed_km_per_hour: float = 50.0
    ) -> Dict[str, Any]:
        """
        Solve the Vehicle Routing Problem with Time Windows.

        Args:
            distance_matrix: 2D numpy array of distances between locations.
            location_ids: List of location IDs corresponding to matrix indices.
            vehicles: List of Vehicle objects.
            deliveries: List of Delivery objects.
            locations: List of Location objects with time windows.
            depot_index: Index of the depot location in the distance matrix.
            speed_km_per_hour: Average vehicle speed in kilometers per hour.

        Returns:
            Dictionary containing the solution details with route time information.
        """
        # Similar to solve() but with additional time window constraints
        # Implement time windows using OR-Tools Dimension constraints
        
        # Create index manager and routing model as in solve()
        num_locations = len(location_ids)
        num_vehicles = len(vehicles)
        
        # Create location_id to index mapping
        location_id_to_index = {loc_id: idx for idx, loc_id in enumerate(location_ids)}
        location_index_to_location = {idx: next((loc for loc in locations if loc.id == loc_id), None)
                                     for idx, loc_id in enumerate(location_ids)}
        
        # Map vehicle start/end locations to indices
        starts = []
        ends = []
        
        for vehicle in vehicles:
            try:
                start_idx = location_id_to_index[vehicle.start_location_id]
                # If end location not specified, use the start location
                end_idx = location_id_to_index.get(
                    vehicle.end_location_id or vehicle.start_location_id,
                    start_idx
                )
                starts.append(start_idx)
                ends.append(end_idx)
            except KeyError as e:
                logger.error(f"Vehicle location not found in locations: {e}")
                return {
                    'status': 'failed',
                    'error': f"Vehicle location not found: {e}"
                }
        
        manager = pywrapcp.RoutingIndexManager(
            num_locations, 
            num_vehicles,
            starts,
            ends
        )
        
        # Create Routing Model
        routing = pywrapcp.RoutingModel(manager)
        
        # Create and register distance callback
        def distance_callback(from_index, to_index):
            """Returns the distance between the two nodes."""
            from_node = manager.IndexToNode(from_index)
            to_node = manager.IndexToNode(to_index)
            return int(distance_matrix[from_node][to_node] * 1000)  # Convert to int for OR-Tools
        
        transit_callback_index = routing.RegisterTransitCallback(distance_callback)
        routing.SetArcCostEvaluatorOfAllVehicles(transit_callback_index)
        
        # Create and register time callback
        def time_callback(from_index, to_index):
            """Returns the travel time between locations in minutes."""
            from_node = manager.IndexToNode(from_index)
            to_node = manager.IndexToNode(to_index)
            
            # Distance in kilometers
            distance_km = distance_matrix[from_node][to_node]
            
            # Convert to minutes: (distance / speed) * 60
            travel_time_minutes = (distance_km / speed_km_per_hour) * 60
            
            # Add service time for the destination
            to_location = location_index_to_location.get(to_node)
            service_time = to_location.service_time if to_location else 0
            
            return int((travel_time_minutes + service_time) * 60)  # Convert to seconds as int
        
        time_callback_index = routing.RegisterTransitCallback(time_callback)
        
        # Add time dimension
        routing.AddDimension(
            time_callback_index,
            # Allow waiting time at locations
            3600,  # Maximum wait time in seconds (1 hour)
            # Maximum time per vehicle in seconds (24 hours)
            86400,
            # Force start cumul to zero
            False,
            'Time'
        )
        
        time_dimension = routing.GetDimensionOrDie('Time')
        
        # Add time window constraints
        for location_idx, location_id in enumerate(location_ids):
            location = next((loc for loc in locations if loc.id == location_id), None)
            
            if location and location.time_window_start is not None and location.time_window_end is not None:
                # Convert minutes from midnight to seconds
                start_seconds = location.time_window_start * 60
                end_seconds = location.time_window_end * 60
                
                index = manager.NodeToIndex(location_idx)
                time_dimension.CumulVar(index).SetRange(start_seconds, end_seconds)
        
        # Add capacity constraints as in solve()
        # ... (same capacity code as in the solve method)
        
        # Solve and return results
        search_parameters = pywrapcp.DefaultRoutingSearchParameters()
        search_parameters.first_solution_strategy = (
            routing_enums_pb2.FirstSolutionStrategy.PATH_CHEAPEST_ARC
        )
        search_parameters.local_search_metaheuristic = (
            routing_enums_pb2.LocalSearchMetaheuristic.GUIDED_LOCAL_SEARCH
        )
        search_parameters.time_limit.seconds = self.time_limit_seconds
        
        solution = routing.SolveWithParameters(search_parameters)
        
        # Process solution similarly to solve() but with time information
        if solution:
            # Process solution (similar to solve but with time window info)
            # ...
            return {
                'status': 'success',
                # Add route details with time window information
                # ...
            }
        else:
            return {
                'status': 'failed',
                'error': 'No solution found with time window constraints!'
            }