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

class AssignmentPlanner:
    def __init__(self, vehicles: List[FleetVehicleModel], shipments: List[ShipmentModel]):
        self.fleet_vehicles: List[FleetVehicleModel] = vehicles
        self.shipments_to_plan: List[ShipmentModel] = shipments
        self.location_dto_map: Dict[str, LocationDTO] = {}
        self.location_id_to_coords: Dict[str, Dict[str, float]] = {}
        # Initialize optimizer_vehicles and optimizer_deliveries as instance attributes
        self.optimizer_vehicles: List[VehicleDataclass] = []
        self.optimizer_deliveries: List[DeliveryDataclass] = []
        self.optimizer_task_to_shipment_role: Dict[str, Tuple[ShipmentModel, str]] = {}


    def _get_or_create_location_dto(self, lat: float, lng: float, is_depot: bool = False, service_time: int = 0) -> LocationDTO:
        loc_key = f"{lat:.6f}_{lng:.6f}"
        if loc_key not in self.location_dto_map:
            loc_id = str(uuid.uuid4())
            location_dto = LocationDTO(
                id=loc_id,
                latitude=lat,
                longitude=lng,
                is_depot=is_depot,
                service_time=service_time
            )
            self.location_dto_map[loc_key] = location_dto
            self.location_id_to_coords[loc_id] = {"lat": lat, "lng": lng}
            return location_dto
        return self.location_dto_map[loc_key]

    def plan_assignments(self) -> List[Assignment]:
        logger.info("Planning assignments started using ORToolsVRPSolver.")

        # Clear previous planning data
        self.optimizer_vehicles.clear()
        self.optimizer_deliveries.clear()
        self.location_dto_map.clear()
        self.location_id_to_coords.clear()
        self.optimizer_task_to_shipment_role.clear()


        if not self.fleet_vehicles:
            logger.warning("No vehicles provided for assignment planning.")
            return []
        if not self.shipments_to_plan:
            logger.info("No shipments to plan.")
            return []

        # Use self.optimizer_vehicles
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
                id=str(fleet_vehicle.vehicle_id),
                capacity=float(fleet_vehicle.capacity),
                start_location_id=depot_location_dto.id,
                end_location_id=depot_location_dto.id,
            )
            self.optimizer_vehicles.append(vehicle_dc) # Modified
        logger.info(f"{len(self.optimizer_vehicles)} vehicles prepared for VRP input.")
        
        if not self.optimizer_vehicles: # Modified
            logger.error("No suitable vehicles with depot information found for planning.")
            # Changed from Exception to return [] as per test_all_vehicles_missing_depot_coordinates_raises_exception expectation might change
            # raise Exception("Optimization failed: No valid vehicles for planning.")
            return [] # Match behavior if no valid vehicles

        # Use self.optimizer_deliveries and self.optimizer_task_to_shipment_role
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
            self.optimizer_deliveries.append(DeliveryDataclass( # Modified
                id=pickup_task_id,
                location_id=pickup_loc_dto.id,
                demand=float(shipment.demand),
                is_pickup=True,
                priority=DEFAULT_DELIVERY_PRIORITY 
            ))
            self.optimizer_task_to_shipment_role[pickup_task_id] = (shipment, "pickup") # Modified

            delivery_task_id = f"{shipment.id}_delivery"
            self.optimizer_deliveries.append(DeliveryDataclass( # Modified
                id=delivery_task_id,
                location_id=delivery_loc_dto.id,
                demand=float(shipment.demand),
                is_pickup=False,
                priority=DEFAULT_DELIVERY_PRIORITY
            ))
            self.optimizer_task_to_shipment_role[delivery_task_id] = (shipment, "delivery") # Modified
        
        logger.info(f"{len(self.optimizer_deliveries)} optimizer delivery tasks created for {len(self.shipments_to_plan)} shipments.")

        if not self.optimizer_deliveries: # Modified
            logger.info("No valid delivery tasks to optimize after processing shipments.")
            return []

        all_location_dtos_list = list(self.location_dto_map.values())
        
        logger.debug(f"Creating distance matrix for {len(all_location_dtos_list)} unique locations.")
        dist_matrix_builder = DistanceMatrixBuilder()
        try:
            matrix_data = dist_matrix_builder.create_distance_matrix(
                locations=all_location_dtos_list, 
                use_haversine=True, 
                use_api=False
            )
            distance_matrix_km, _time_matrix_minutes, ordered_location_ids_from_matrix = matrix_data
        except Exception as e:
            logger.error(f"Failed to create distance matrix: {e}", exc_info=True)
            raise Exception(f"Optimization failed: Could not create distance matrix - {e}")

        logger.debug(f"Distance matrix created. Shape: {distance_matrix_km.shape if distance_matrix_km is not None else 'None'}")

        solver = ORToolsVRPSolver()
        optimization_result: OptimizationResult = solver.solve(
            distance_matrix=distance_matrix_km,
            location_ids=ordered_location_ids_from_matrix,
            vehicles=self.optimizer_vehicles, # Modified
            deliveries=self.optimizer_deliveries # Modified
        )
        logger.info(f"Optimizer finished solving. Status: {optimization_result.status}")

        if optimization_result.status != 'success':
            error_msg = optimization_result.statistics.get('error', 'Unknown error from solver')
            logger.error(f"Optimizer failed to find a solution: {error_msg}")
            raise Exception(f"Optimization failed: {error_msg}")

        created_assignments: List[Assignment] = []
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
            
            current_route_total_load = 0
            route_shipment_tasks_for_load_calc = set()
            stop_location_dto_ids_in_route = detailed_route_dict.get('stops', [])
            
            for opt_delivery_task in self.optimizer_deliveries: # Modified
                if opt_delivery_task.location_id in stop_location_dto_ids_in_route:
                    original_shipment_model, role = self.optimizer_task_to_shipment_role.get(opt_delivery_task.id, (None, "")) # Modified
                    if original_shipment_model and role == "delivery":
                        route_shipment_tasks_for_load_calc.add(original_shipment_model.id)
            
            for shipment_model_id in route_shipment_tasks_for_load_calc:
                 original_shipment = next((s for s in self.shipments_to_plan if s.id == shipment_model_id), None)
                 if original_shipment:
                     current_route_total_load += original_shipment.demand

            assignment = Assignment.objects.create(
                vehicle=assigned_fleet_vehicle,
                total_load=int(current_route_total_load),
                status='created'
            )

            assigned_fleet_vehicle.status = "assigned"
            assigned_fleet_vehicle.save(update_fields=["status", "updated_at"])

            seq = 1
            for stop_loc_dto_id in stop_location_dto_ids_in_route:
                tasks_at_this_stop = [
                    task for task in self.optimizer_deliveries # Modified
                    if task.location_id == stop_loc_dto_id
                ]
                current_location_dto = next((loc for loc_id, loc in self.location_dto_map.items() if loc.id == stop_loc_dto_id), None) # Check key for self.location_dto_map or direct value access
                
                is_depot_stop_without_tasks = current_location_dto and current_location_dto.is_depot and not tasks_at_this_stop
                if is_depot_stop_without_tasks:
                    # logger.debug(f"Stop {stop_loc_dto_id} is a depot without tasks. Skipping AssignmentItem creation.")
                    continue

                for opt_task in tasks_at_this_stop:
                    shipment_model, role = self.optimizer_task_to_shipment_role.get(opt_task.id, (None, "")) # Modified
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
                        delivery_location=actual_stop_coords,
                        role=role
                    )
                    seq += 1
            
            created_assignments.append(assignment)

        logger.info(f"{len(created_assignments)} assignments successfully created.")
        return created_assignments