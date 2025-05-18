import logging
import uuid
from typing import List, Dict, Tuple

from assignment.models.assignment import Assignment
from assignment.models.assignment_item import AssignmentItem
from fleet.models import Vehicle as FleetVehicleModel # Renamed to avoid confusion
from shipments.models import Shipment as ShipmentModel # Renamed to avoid confusion

from route_optimizer.core.ortools_optimizer import ORToolsVRPSolver
from route_optimizer.core.types_1 import Location as LocationDTO, OptimizationResult
from route_optimizer.models.base import Vehicle as VehicleDataclass, Delivery as DeliveryDataclass
from route_optimizer.core.distance_matrix import DistanceMatrixBuilder
from route_optimizer.core.constants import DEFAULT_DELIVERY_PRIORITY


logger = logging.getLogger(__name__)
# logging.basicConfig(level=logging.DEBUG) # Usually configured in Django settings

class AssignmentPlanner:
    def __init__(self, vehicles: List[FleetVehicleModel], shipments: List[ShipmentModel]):
        self.fleet_vehicles: List[FleetVehicleModel] = vehicles
        self.shipments_to_plan: List[ShipmentModel] = shipments
        self.location_dto_map: Dict[str, LocationDTO] = {} # Maps unique string (e.g. "lat_lng") to LocationDTO
        self.location_id_to_coords: Dict[str, Dict[str, float]] = {} # Maps LocationDTO.id to {"lat": ..., "lng": ...}

    def _get_or_create_location_dto(self, lat: float, lng: float, is_depot: bool = False, service_time: int = 0) -> LocationDTO:
        """Creates or retrieves a LocationDTO, ensuring unique IDs."""
        # Using lat_lng as a simple key for uniqueness in this example.
        # For production, consider a more robust way if precision issues arise.
        loc_key = f"{lat:.6f}_{lng:.6f}" # Key based on coordinates
        if loc_key not in self.location_dto_map:
            loc_id = str(uuid.uuid4()) # Generate a unique ID for the optimizer
            location_dto = LocationDTO(
                id=loc_id,
                latitude=lat,
                longitude=lng,
                is_depot=is_depot,
                service_time=service_time # Default service time
                # time_window_start, time_window_end can be added if needed
            )
            self.location_dto_map[loc_key] = location_dto
            self.location_id_to_coords[loc_id] = {"lat": lat, "lng": lng}
            return location_dto
        return self.location_dto_map[loc_key]

    def plan_assignments(self) -> List[Assignment]:
        logger.info("Planning assignments started using ORToolsVRPSolver.")

        if not self.fleet_vehicles:
            logger.warning("No vehicles provided for assignment planning.")
            # Depending on desired behavior, either return [] or raise error
            # raise AssertionError("No vehicles available for planning.")
            return [] 
        if not self.shipments_to_plan:
            logger.info("No shipments to plan.")
            return []

        optimizer_vehicles: List[VehicleDataclass] = []
        optimizer_deliveries: List[DeliveryDataclass] = []
        
        # Map fleet.models.Vehicle to route_optimizer.models.base.Vehicle (VehicleDataclass)
        # and collect depot locations
        for fleet_vehicle in self.fleet_vehicles:
            if fleet_vehicle.depot_latitude is None or fleet_vehicle.depot_longitude is None:
                logger.warning(f"Vehicle {fleet_vehicle.vehicle_id} is missing depot coordinates. Skipping.")
                continue

            depot_location_dto = self._get_or_create_location_dto(
                lat=fleet_vehicle.depot_latitude,
                lng=fleet_vehicle.depot_longitude,
                is_depot=True
            )
            
            vehicle_dc = VehicleDataclass(
                id=str(fleet_vehicle.vehicle_id), # Ensure ID is string
                capacity=float(fleet_vehicle.capacity), # Optimizer expects float
                start_location_id=depot_location_dto.id,
                end_location_id=depot_location_dto.id, # Assuming vehicles return to their start depot
                # cost_per_km, fixed_cost, max_distance, etc., can be set if available on FleetVehicleModel
            )
            optimizer_vehicles.append(vehicle_dc)
        logger.info(f"{len(optimizer_vehicles)} vehicles prepared for VRP input.")
        
        if not optimizer_vehicles:
            logger.error("No suitable vehicles with depot information found for planning.")
            raise Exception("Optimization failed: No valid vehicles for planning.")

        # Map shipments.models.Shipment to route_optimizer.models.base.Delivery (DeliveryDataclass)
        # and collect pickup/delivery locations
        # Also, create a map from optimizer task ID back to original shipment and role
        optimizer_task_to_shipment_role: Dict[str, Tuple[ShipmentModel, str]] = {}

        for shipment in self.shipments_to_plan:
            try:
                origin_lat = float(shipment.origin["lat"])
                origin_lng = float(shipment.origin["lng"])
                dest_lat = float(shipment.destination["lat"])
                dest_lng = float(shipment.destination["lng"])
            except (TypeError, KeyError, ValueError) as e:
                logger.error(f"Shipment {shipment.shipment_id} has invalid origin/destination coordinates: {e}. Skipping.")
                continue

            pickup_loc_dto = self._get_or_create_location_dto(lat=origin_lat, lng=origin_lng)
            delivery_loc_dto = self._get_or_create_location_dto(lat=dest_lat, lng=dest_lng)

            pickup_task_id = f"{shipment.id}_pickup"
            optimizer_deliveries.append(DeliveryDataclass(
                id=pickup_task_id,
                location_id=pickup_loc_dto.id,
                demand=float(shipment.demand),
                is_pickup=True,
                priority=DEFAULT_DELIVERY_PRIORITY 
            ))
            optimizer_task_to_shipment_role[pickup_task_id] = (shipment, "pickup")

            delivery_task_id = f"{shipment.id}_delivery"
            optimizer_deliveries.append(DeliveryDataclass(
                id=delivery_task_id,
                location_id=delivery_loc_dto.id,
                demand=float(shipment.demand), # Demand is positive; solver handles capacity effect with is_pickup
                is_pickup=False,
                priority=DEFAULT_DELIVERY_PRIORITY
            ))
            optimizer_task_to_shipment_role[delivery_task_id] = (shipment, "delivery")
        
        logger.info(f"{len(optimizer_deliveries)} optimizer delivery tasks created for {len(self.shipments_to_plan)} shipments.")

        if not optimizer_deliveries:
            logger.info("No valid delivery tasks to optimize after processing shipments.")
            # Create empty assignments for vehicles if that's desired, or return empty list
            # For now, let's assume if no deliveries, no assignments are made beyond empty routes for vehicles.
            # ORToolsVRPSolver's solve() method with empty deliveries will create depot-to-depot routes.
            # We can decide if we want to persist these as "empty" assignments.
            # For now, if no actual deliveries, we'll return an empty list of assignments.
            return []


        # Prepare list of all unique LocationDTOs for the distance matrix
        all_location_dtos_list = list(self.location_dto_map.values())
        
        # Create Distance Matrix
        # Note: DistanceMatrixBuilder might require API keys or specific configurations
        # For simplicity, using Haversine. Ensure this aligns with your project setup.
        # The builder returns (distance_matrix_km, time_matrix_minutes, location_ids_ordered)
        logger.debug(f"Creating distance matrix for {len(all_location_dtos_list)} unique locations.")
        dist_matrix_builder = DistanceMatrixBuilder()
        # Ensure create_distance_matrix can handle LocationDTOs. If it expects dicts, convert them.
        # For now, assuming it can take LocationDTOs.
        try:
            # Using use_haversine=True as a default, adjust if API is preferred/configured
            matrix_data = dist_matrix_builder.create_distance_matrix(
                locations=all_location_dtos_list, 
                use_haversine=True, 
                use_api=False # Avoid API calls unless explicitly configured
            )
            distance_matrix_km, _time_matrix_minutes, ordered_location_ids_from_matrix = matrix_data
        except Exception as e:
            logger.error(f"Failed to create distance matrix: {e}", exc_info=True)
            raise Exception(f"Optimization failed: Could not create distance matrix - {e}")

        logger.debug(f"Distance matrix created. Shape: {distance_matrix_km.shape if distance_matrix_km is not None else 'None'}")

        # Solve VRP
        solver = ORToolsVRPSolver()
        # The `depot_index` in `solve()` is a global fallback if vehicles don't have start/end_location_id.
        # Our VehicleDataclass has start_location_id, so ORToolsVRPSolver will use those.
        # It internally maps location_ids to indices.
        optimization_result: OptimizationResult = solver.solve(
            distance_matrix=distance_matrix_km,
            location_ids=ordered_location_ids_from_matrix, # Use the ordered list from matrix builder
            vehicles=optimizer_vehicles,
            deliveries=optimizer_deliveries
            # time_matrix can be passed if available and time constraints are used
        )
        logger.info(f"Optimizer finished solving. Status: {optimization_result.status}")

        if optimization_result.status != 'success':
            error_msg = optimization_result.statistics.get('error', 'Unknown error from solver')
            logger.error(f"Optimizer failed to find a solution: {error_msg}")
            raise Exception(f"Optimization failed: {error_msg}")

        # Process solution and create Assignment DB objects
        created_assignments: List[Assignment] = []
        
        # Map fleet vehicle IDs to their Django model instances for easy lookup
        fleet_vehicle_model_map = {str(fv.vehicle_id): fv for fv in self.fleet_vehicles}

        for detailed_route_dict in optimization_result.detailed_routes:
            vehicle_optimizer_id = detailed_route_dict.get('vehicle_id')
            if not vehicle_optimizer_id:
                logger.warning(f"Route found without a vehicle_id in detailed_routes: {detailed_route_dict}. Skipping.")
                continue

            assigned_fleet_vehicle = fleet_vehicle_model_map.get(str(vehicle_optimizer_id))
            if not assigned_fleet_vehicle:
                logger.error(f"Could not find original FleetVehicleModel for optimizer vehicle ID {vehicle_optimizer_id}. Skipping route.")
                continue

            # Calculate total load for this assignment (sum of demands of non-pickup tasks in this route)
            current_route_total_load = 0
            route_shipment_tasks_for_load_calc = set() # To avoid double counting demand if pickup & delivery of same shipment are on route

            # Get stop location_ids for the current route
            # These are DTO Location IDs (UUIDs in our case)
            stop_location_dto_ids_in_route = detailed_route_dict.get('stops', [])
            
            # Iterate through all optimizer_deliveries to find those that are part of this route
            # and are actual deliveries (not pickups) to sum their original demand.
            for opt_delivery_task in optimizer_deliveries:
                # Check if this task's location_id is in the current route's stops
                if opt_delivery_task.location_id in stop_location_dto_ids_in_route:
                    original_shipment_model, role = optimizer_task_to_shipment_role.get(opt_delivery_task.id, (None, ""))
                    if original_shipment_model and role == "delivery": # Sum demand for 'delivery' roles
                        route_shipment_tasks_for_load_calc.add(original_shipment_model.id)
            
            for shipment_model_id in route_shipment_tasks_for_load_calc:
                 # Find the original shipment to get its demand
                 original_shipment = next((s for s in self.shipments_to_plan if s.id == shipment_model_id), None)
                 if original_shipment:
                     current_route_total_load += original_shipment.demand

            assignment = Assignment.objects.create(
                vehicle=assigned_fleet_vehicle,
                total_load=int(current_route_total_load), # Assignment model expects PositiveIntegerField
                status='created'
            )

            assigned_fleet_vehicle.status = "assigned" # From fleet.models.Vehicle.STATUS_CHOICES
            assigned_fleet_vehicle.save(update_fields=["status", "updated_at"])

            seq = 1
            # The 'stops' in detailed_route_dict are location_ids (UUIDs)
            for stop_loc_dto_id in stop_location_dto_ids_in_route:
                # Find all optimizer tasks associated with this stop_loc_dto_id
                tasks_at_this_stop = [
                    task for task in optimizer_deliveries 
                    if task.location_id == stop_loc_dto_id
                ]

                # Check if this stop is a depot. If so, usually no AssignmentItem.
                # This check relies on LocationDTO.is_depot being set correctly.
                current_location_dto = next((loc for loc_key, loc in self.location_dto_map.items() if loc.id == stop_loc_dto_id), None)
                if current_location_dto and current_location_dto.is_depot:
                    # logger.debug(f"Stop {stop_loc_dto_id} is a depot. Skipping AssignmentItem creation.")
                    # Continue to next stop unless specific depot actions are needed.
                    # For now, if it's a depot, we only create items if there are actual pickup/delivery tasks there.
                    # If tasks_at_this_stop is empty for a depot, it's just a pass-through or start/end.
                    pass


                for opt_task in tasks_at_this_stop:
                    # Make sure this task was actually part of this vehicle's route
                    # (A bit redundant if detailed_routes only contain tasks for that route, but good for safety)
                    # This check is complex as opt_task.id needs to be mapped back to a stop in the *solution* for *this* vehicle.
                    # OR-Tools solution provides a sequence of nodes. `detailed_routes[X].stops` IS that sequence.
                    # So if opt_task.location_id is in `stop_location_dto_ids_in_route`, it's on the route.

                    shipment_model, role = optimizer_task_to_shipment_role.get(opt_task.id, (None, ""))
                    if not shipment_model:
                        logger.warning(f"Could not map optimizer task ID {opt_task.id} back to a shipment. Skipping AssignmentItem.")
                        continue
                    
                    actual_stop_coords = self.location_id_to_coords.get(stop_loc_dto_id)
                    if not actual_stop_coords:
                        logger.error(f"Could not find coordinates for location DTO ID {stop_loc_dto_id}. Skipping AssignmentItem.")
                        continue

                    logger.debug(f"Adding {role} for shipment {shipment_model.shipment_id} (Task ID: {opt_task.id}) at sequence {seq} for Assignment {assignment.id}")
                    AssignmentItem.objects.create(
                        assignment=assignment,
                        shipment=shipment_model,
                        delivery_sequence=seq,
                        delivery_location=actual_stop_coords, # e.g. {"lat": ..., "lng": ...}
                        role=role
                    )
                    seq += 1 # Increment sequence for each actual task processed.
            
            created_assignments.append(assignment)

        logger.info(f"{len(created_assignments)} assignments successfully created.")
        return created_assignments

