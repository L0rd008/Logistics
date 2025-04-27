"""
Optimization service that integrates different optimization algorithms.

This service provides a high-level interface to the route optimization
capabilities, integrating Dijkstra's algorithm and OR-Tools.
"""
import logging
from typing import Dict, List, Tuple, Optional, Any, Union
import numpy as np

from route_optimizer.core.dijkstra import DijkstraPathFinder
from route_optimizer.core.ortools_optimizer import ORToolsVRPSolver, Vehicle, Delivery
from route_optimizer.core.distance_matrix import DistanceMatrixBuilder, Location

# Set up logging
logger = logging.getLogger(__name__)


class OptimizationService:
    """
    Service for optimizing delivery routes.
    """
    
    def __init__(self, time_limit_seconds: int = 30):
        """
        Initialize the optimization service.
        
        Args:
            time_limit_seconds: Time limit for the solver in seconds.
        """
        self.vrp_solver = ORToolsVRPSolver(time_limit_seconds=time_limit_seconds)
        self.path_finder = DijkstraPathFinder()
    
    def optimize_routes(
        self,
        locations: List[Location],
        vehicles: List[Vehicle],
        deliveries: List[Delivery],
        consider_traffic: bool = False,
        consider_time_windows: bool = False,
        traffic_data: Optional[Dict[Tuple[int, int], float]] = None
    ) -> Dict[str, Any]:
        """
        Optimize delivery routes based on locations, vehicles, and deliveries.
        
        Args:
            locations: List of Location objects.
            vehicles: List of Vehicle objects.
            deliveries: List of Delivery objects.
            consider_traffic: Whether to consider traffic data.
            consider_time_windows: Whether to consider time windows.
            traffic_data: Dictionary mapping (i,j) tuples to traffic factors.

        Returns:
            Dictionary containing the optimization results.
        """
        # Create distance matrix
        distance_matrix, location_ids = DistanceMatrixBuilder.create_distance_matrix(
            locations, use_haversine=True
        )
        
        # Apply traffic factors if needed
        if consider_traffic and traffic_data is not None:
            distance_matrix = DistanceMatrixBuilder.add_traffic_factors(
                distance_matrix, traffic_data
            )
        
        # Find depot index (default to 0 if no depot is specified)
        depot_indices = [i for i, loc in enumerate(locations) if loc.is_depot]
        depot_index = depot_indices[0] if depot_indices else 0
        
        # Solve the VRP
        if consider_time_windows:
            result = self.vrp_solver.solve_with_time_windows(
                distance_matrix=distance_matrix,
                location_ids=location_ids,
                vehicles=vehicles,
                deliveries=deliveries,
                locations=locations,
                depot_index=depot_index
            )
        else:
            result = self.vrp_solver.solve(
                distance_matrix=distance_matrix,
                location_ids=location_ids,
                vehicles=vehicles,
                deliveries=deliveries,
                depot_index=depot_index
            )
        
        # If optimization successful, add detailed path information using Dijkstra
        if result['status'] == 'success':
            # Convert distance matrix to graph for Dijkstra
            graph = DistanceMatrixBuilder.distance_matrix_to_graph(
                distance_matrix, location_ids
            )
            
            # Add detailed paths to each route
            self._add_detailed_paths(result, graph)
            
            # Calculate and add summary statistics
            self._add_summary_statistics(result, vehicles)
        
        return result
    
    def _add_detailed_paths(self, result: Dict[str, Any], graph: Dict[str, Dict[str, float]]) -> None:
        """
        Add detailed path information to the optimization result.
        
        Args:
            result: Optimization result dictionary to update.
            graph: Graph representation of the distance matrix.
        """
        detailed_routes = []
        
        for route in result['routes']:
            detailed_route = {
                'stops': route,
                'segments': []
            }
            
            # Process each segment in the route
            for i in range(len(route) - 1):
                from_location = route[i]
                to_location = route[i + 1]
                
                # Get detailed path using Dijkstra
                path, distance = self.path_finder.calculate_shortest_path(
                    graph, from_location, to_location
                )
                
                if path:
                    detailed_route['segments'].append({
                        'from': from_location,
                        'to': to_location,
                        'path': path,
                        'distance': distance
                    })
            
            detailed_routes.append(detailed_route)
        
        result['detailed_routes'] = detailed_routes
    
    def _add_summary_statistics(self, result: Dict[str, Any], vehicles: List[Vehicle]) -> None:
        """
        Add summary statistics to the optimization result.
        
        Args:
            result: Optimization result dictionary to update.
            vehicles: List of Vehicle objects.
        """
        # Calculate cost per vehicle
        vehicle_costs = {}
        total_cost = 0
        
        for vehicle_id, route_idx in result['assigned_vehicles'].items():
            # Find corresponding vehicle object
            vehicle = next((v for v in vehicles if v.id == vehicle_id), None)
            
            if vehicle:
                # Get route distance
                route_distance = 0
                for segment in result['detailed_routes'][route_idx]['segments']:
                    route_distance += segment['distance']
                
                # Calculate cost
                cost = vehicle.fixed_cost + (route_distance * vehicle.cost_per_km)
                vehicle_costs[vehicle_id] = {
                    'distance': route_distance,
                    'cost': cost
                }
                total_cost += cost
        
        result['vehicle_costs'] = vehicle_costs
        result['total_cost'] = total_cost
        
        # Calculate other statistics: total distance, avg distance per stop, etc.
        total_stops = sum(len(route['stops']) for route in result['detailed_routes'])
        result['total_stops'] = total_stops
        
        if total_stops > 0:
            result['avg_distance_per_stop'] = result['total_distance'] / total_stops
        
        # Count used/unused vehicles
        result['vehicles_used'] = len(result['assigned_vehicles'])
        result['vehicles_unused'] = len(vehicles) - result['vehicles_used']