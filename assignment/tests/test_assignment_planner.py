import uuid
import logging
from unittest.mock import patch, MagicMock

from django.test import TestCase
from django.utils import timezone

from fleet.models import Vehicle as FleetVehicleModel
from shipments.models import Shipment as ShipmentModel
from assignment.models import Assignment, AssignmentItem 
from assignment.services.assignment_planner import AssignmentPlanner

from route_optimizer.core.types_1 import OptimizationResult, Location as LocationDTO
from route_optimizer.models.base import Vehicle as VehicleDataclass, Delivery as DeliveryDataclass
import numpy as np

# Disable logging for cleaner test output
logging.disable(logging.CRITICAL)


class AssignmentPlannerDetailedTests(TestCase):
    def setUp(self):
        self.vehicle1_id = str(uuid.uuid4())
        self.vehicle1 = FleetVehicleModel.objects.create(
            vehicle_id=self.vehicle1_id,
            name="Test Truck 1",
            capacity=1000,
            depot_latitude=6.900000,
            depot_longitude=79.850000,
            status="available"
        )

        self.vehicle2_id = str(uuid.uuid4())
        self.vehicle2 = FleetVehicleModel.objects.create(
            vehicle_id=self.vehicle2_id,
            name="Test Truck 2",
            capacity=1500,
            depot_latitude=7.000000,
            depot_longitude=80.000000,
            status="available"
        )

        self.shipment1 = ShipmentModel.objects.create(
            shipment_id="SHIP001",
            order_id="ORDER001",
            origin={"lat": 6.927079, "lng": 79.861244},
            destination={"lat": 7.290572, "lng": 80.633728},
            demand=100,
            status="pending"
        )

        self.shipment2 = ShipmentModel.objects.create(
            shipment_id="SHIP002",
            order_id="ORDER002",
            origin={"lat": 6.053519, "lng": 80.220978},
            destination={"lat": 6.8439, "lng": 79.9989},
            demand=200,
            status="pending"
        )

    def _get_default_mock_matrix_data(self, location_ids):
        size = len(location_ids)
        return (
            np.random.rand(size, size) * 100,
            np.random.rand(size, size) * 60,
            location_ids
        )

    def test_plan_assignments_no_vehicles(self):
        planner = AssignmentPlanner(vehicles=[], shipments=[self.shipment1])
        assignments = planner.plan_assignments()
        self.assertEqual(len(assignments), 0)

    def test_plan_assignments_no_shipments(self):
        planner = AssignmentPlanner(vehicles=[self.vehicle1], shipments=[])
        assignments = planner.plan_assignments()
        self.assertEqual(len(assignments), 0)

    def test_vehicle_missing_depot_coordinates(self):
        self.vehicle1.depot_latitude = None
        self.vehicle1.save()
        planner = AssignmentPlanner(vehicles=[self.vehicle1, self.vehicle2], shipments=[self.shipment1])
        
        def mock_solve_interaction(*args, **kwargs_solve):
            # Dynamically find location IDs for vehicle2's depot and shipment1's tasks
            v2_depot_id, s1_pickup_id, s1_delivery_id = "", "", ""
            for loc_key, loc_dto in planner.location_dto_map.items():
                coords = (loc_dto.latitude, loc_dto.longitude)
                if coords == (self.vehicle2.depot_latitude, self.vehicle2.depot_longitude):
                    v2_depot_id = loc_dto.id
                elif coords == (float(self.shipment1.origin["lat"]), float(self.shipment1.origin["lng"])):
                    s1_pickup_id = loc_dto.id
                elif coords == (float(self.shipment1.destination["lat"]), float(self.shipment1.destination["lng"])):
                    s1_delivery_id = loc_dto.id
            
            self.assertTrue(v2_depot_id and s1_pickup_id and s1_delivery_id, "Failed to find dynamic location IDs in mock_solve_interaction for vehicle_missing_depot_coordinates test")

            mock_detailed_route_v2 = {
                "vehicle_id": self.vehicle2.vehicle_id, # vehicle_id is a string
                "stops": [v2_depot_id, s1_pickup_id, s1_delivery_id, v2_depot_id],
            }
            return OptimizationResult(
                status="success",
                detailed_routes=[mock_detailed_route_v2],
                assigned_vehicles={self.vehicle2.vehicle_id: 0},
                statistics={}
            )

        with patch('assignment.services.assignment_planner.DistanceMatrixBuilder') as MockMatrixBuilder:
            mock_matrix_instance = MockMatrixBuilder.return_value
            def side_effect_create_matrix(*args, **kwargs_matrix):
                planner_loc_ids_str = [loc.id for loc in kwargs_matrix['locations']]
                return self._get_default_mock_matrix_data(planner_loc_ids_str)
            mock_matrix_instance.create_distance_matrix.side_effect = side_effect_create_matrix

            with patch('assignment.services.assignment_planner.ORToolsVRPSolver') as MockSolver:
                mock_solver_instance = MockSolver.return_value
                mock_solver_instance.solve.side_effect = mock_solve_interaction
                
                assignments = planner.plan_assignments()

        self.assertEqual(len(assignments), 1)
        self.assertEqual(assignments[0].vehicle, self.vehicle2)
        # Accessing planner.optimizer_vehicles to check which vehicles were processed
        self.assertEqual(len(planner.optimizer_vehicles), 1) 
        self.assertEqual(planner.optimizer_vehicles[0].id, str(self.vehicle2.vehicle_id))


    def test_all_vehicles_missing_depot_coordinates_returns_empty(self): # Renamed from _raises_exception based on current planner logic
        self.vehicle1.depot_latitude = None
        self.vehicle1.save()
        self.vehicle2.depot_longitude = None
        self.vehicle2.save()
        planner = AssignmentPlanner(vehicles=[self.vehicle1, self.vehicle2], shipments=[self.shipment1])
        # Current planner logic returns empty list if no suitable vehicles, not raises Exception
        assignments = planner.plan_assignments()
        self.assertEqual(len(assignments), 0)

    def test_shipment_invalid_coordinates(self):
        self.shipment1.origin = {"lat_bad": "invalid", "lng": "invalid"}
        self.shipment1.save()
        
        planner = AssignmentPlanner(vehicles=[self.vehicle1], shipments=[self.shipment1, self.shipment2])

        def mock_solve_interaction(*args, **kwargs_solve):
            v1_depot_id, s2_pickup_id, s2_delivery_id = "", "", ""
            for loc_key, loc_dto in planner.location_dto_map.items():
                coords = (loc_dto.latitude, loc_dto.longitude)
                if coords == (self.vehicle1.depot_latitude, self.vehicle1.depot_longitude):
                    v1_depot_id = loc_dto.id
                elif coords == (float(self.shipment2.origin["lat"]), float(self.shipment2.origin["lng"])):
                    s2_pickup_id = loc_dto.id
                elif coords == (float(self.shipment2.destination["lat"]), float(self.shipment2.destination["lng"])):
                    s2_delivery_id = loc_dto.id
            
            self.assertTrue(v1_depot_id and s2_pickup_id and s2_delivery_id, "Failed to find dynamic location IDs in mock_solve_interaction for shipment_invalid_coordinates test")
            
            mock_detailed_route_s2 = {
                "vehicle_id": self.vehicle1.vehicle_id,
                "stops": [v1_depot_id, s2_pickup_id, s2_delivery_id, v1_depot_id],
            }
            return OptimizationResult(
                status="success",
                detailed_routes=[mock_detailed_route_s2],
                assigned_vehicles={self.vehicle1.vehicle_id: 0},
                statistics={}
            )

        with patch('assignment.services.assignment_planner.DistanceMatrixBuilder') as MockMatrixBuilder:
            mock_matrix_instance = MockMatrixBuilder.return_value
            def side_effect_create_matrix(*args, **kwargs_matrix):
                planner_loc_ids_str = [loc.id for loc in kwargs_matrix['locations']]
                return self._get_default_mock_matrix_data(planner_loc_ids_str)
            mock_matrix_instance.create_distance_matrix.side_effect = side_effect_create_matrix
            
            with patch('assignment.services.assignment_planner.ORToolsVRPSolver') as MockSolver:
                mock_solver_instance = MockSolver.return_value
                mock_solver_instance.solve.side_effect = mock_solve_interaction
                
                assignments = planner.plan_assignments()
        
        self.assertEqual(len(assignments), 1)
        self.assertIsNotNone(assignments[0].items.first(), "Assignment created but has no items.") # Check items exist
        self.assertEqual(assignments[0].items.first().shipment, self.shipment2)
        
        # Check planner's internal state for optimizer_deliveries
        self.assertEqual(len(planner.optimizer_deliveries), 2) # Only for shipment2
        # Ensure shipment.id is converted to string for the 'in' check with task.id
        self.assertTrue(all(str(self.shipment2.id) in task.id for task in planner.optimizer_deliveries))


    def test_all_shipments_invalid_coordinates_returns_empty_list(self):
        self.shipment1.origin = {"lat_bad": "invalid"}
        self.shipment1.save()
        # FIX: Provide invalid JSON structure instead of None for non-nullable field
        self.shipment2.destination = {"error": "destination_coord_invalid"} 
        self.shipment2.save()
        planner = AssignmentPlanner(vehicles=[self.vehicle1], shipments=[self.shipment1, self.shipment2])
        assignments = planner.plan_assignments()
        self.assertEqual(len(assignments), 0)
        # Also check that no optimizer deliveries were prepared
        self.assertEqual(len(planner.optimizer_deliveries), 0)


    def test_distance_matrix_creation_fails_raises_exception(self):
        planner = AssignmentPlanner(vehicles=[self.vehicle1], shipments=[self.shipment1])
        with patch('assignment.services.assignment_planner.DistanceMatrixBuilder') as MockMatrixBuilder:
            mock_matrix_instance = MockMatrixBuilder.return_value
            mock_matrix_instance.create_distance_matrix.side_effect = ValueError("API Error")
            with self.assertRaisesRegex(Exception, "Optimization failed: Could not create distance matrix - API Error"):
                planner.plan_assignments()

    def test_optimizer_fails_to_find_solution_raises_exception(self):
        planner = AssignmentPlanner(vehicles=[self.vehicle1], shipments=[self.shipment1])
        mock_opt_result = OptimizationResult(
            status="failed",
            detailed_routes=[],
            statistics={"error": "Solver timeout"}
        )
        with patch('assignment.services.assignment_planner.DistanceMatrixBuilder') as MockMatrixBuilder:
            mock_matrix_instance = MockMatrixBuilder.return_value
            def side_effect_create_matrix(*args, **kwargs_matrix):
                planner_loc_ids_str = [loc.id for loc in kwargs_matrix['locations']]
                return self._get_default_mock_matrix_data(planner_loc_ids_str)
            mock_matrix_instance.create_distance_matrix.side_effect = side_effect_create_matrix
            
            with patch('assignment.services.assignment_planner.ORToolsVRPSolver') as MockSolver:
                mock_solver_instance = MockSolver.return_value
                mock_solver_instance.solve.return_value = mock_opt_result
                with self.assertRaisesRegex(Exception, "Optimization failed: Solver timeout"):
                    planner.plan_assignments()

    @patch('assignment.services.assignment_planner.ORToolsVRPSolver')
    @patch('assignment.services.assignment_planner.DistanceMatrixBuilder')
    def test_successful_plan_one_vehicle_one_shipment(self, MockMatrixBuilder, MockSolver):
        planner = AssignmentPlanner(vehicles=[self.vehicle1], shipments=[self.shipment1])

        def mock_solve_interaction(*args, **kwargs_solve):
            depot1_actual_id, s1_origin_actual_id, s1_dest_actual_id = "", "", ""
            for loc_key, loc_dto in planner.location_dto_map.items():
                coords = (loc_dto.latitude, loc_dto.longitude)
                if coords == (self.vehicle1.depot_latitude, self.vehicle1.depot_longitude):
                    depot1_actual_id = loc_dto.id
                elif coords == (float(self.shipment1.origin["lat"]), float(self.shipment1.origin["lng"])):
                    s1_origin_actual_id = loc_dto.id
                elif coords == (float(self.shipment1.destination["lat"]), float(self.shipment1.destination["lng"])):
                    s1_dest_actual_id = loc_dto.id
            
            self.assertTrue(depot1_actual_id and s1_origin_actual_id and s1_dest_actual_id)

            mock_detailed_route = {
                "vehicle_id": str(self.vehicle1.vehicle_id),
                "stops": [depot1_actual_id, s1_origin_actual_id, s1_dest_actual_id, depot1_actual_id],
            }
            return OptimizationResult(
                status="success",
                detailed_routes=[mock_detailed_route],
                assigned_vehicles={str(self.vehicle1.vehicle_id): 0},
                unassigned_deliveries=[],
                statistics={}
            )

        mock_matrix_instance = MockMatrixBuilder.return_value
        def side_effect_create_matrix(*args, **kwargs_matrix):
            all_loc_dtos = kwargs_matrix['locations']
            planner_loc_ids_str = [loc.id for loc in all_loc_dtos]
            return self._get_default_mock_matrix_data(planner_loc_ids_str)
        mock_matrix_instance.create_distance_matrix.side_effect = side_effect_create_matrix
        
        mock_solver_instance = MockSolver.return_value
        mock_solver_instance.solve.side_effect = mock_solve_interaction
        
        assignments = planner.plan_assignments()

        self.assertEqual(len(assignments), 1)
        assignment = assignments[0]
        self.assertEqual(assignment.vehicle, self.vehicle1)
        self.assertEqual(assignment.status, "created")
        self.assertEqual(assignment.total_load, self.shipment1.demand) 

        self.vehicle1.refresh_from_db()
        self.assertEqual(self.vehicle1.status, "assigned")

        items = AssignmentItem.objects.filter(assignment=assignment).order_by('delivery_sequence')
        self.assertEqual(items.count(), 2)

        pickup_item = items[0]
        self.assertEqual(pickup_item.shipment, self.shipment1)
        self.assertEqual(pickup_item.role, "pickup")
        self.assertEqual(pickup_item.delivery_sequence, 1)
        self.assertEqual(pickup_item.delivery_location["lat"], float(self.shipment1.origin["lat"]))
        self.assertEqual(pickup_item.delivery_location["lng"], float(self.shipment1.origin["lng"]))

        delivery_item = items[1]
        self.assertEqual(delivery_item.shipment, self.shipment1)
        self.assertEqual(delivery_item.role, "delivery")
        self.assertEqual(delivery_item.delivery_sequence, 2)
        self.assertEqual(delivery_item.delivery_location["lat"], float(self.shipment1.destination["lat"]))
        self.assertEqual(delivery_item.delivery_location["lng"], float(self.shipment1.destination["lng"]))

    @patch('assignment.services.assignment_planner.ORToolsVRPSolver')
    @patch('assignment.services.assignment_planner.DistanceMatrixBuilder')
    def test_optimizer_route_missing_vehicle_id(self, MockMatrixBuilder, MockSolver):
        planner = AssignmentPlanner(vehicles=[self.vehicle1], shipments=[self.shipment1])
        
        mock_detailed_route = {"stops": ["loc1", "loc2"]} 
        mock_opt_result = OptimizationResult(
            status="success",
            detailed_routes=[mock_detailed_route],
            assigned_vehicles={}, statistics={}
        )

        mock_matrix_instance = MockMatrixBuilder.return_value
        def side_effect_create_matrix(*args, **kwargs_matrix):
            planner_loc_ids = [loc.id for loc in kwargs_matrix['locations']]
            return self._get_default_mock_matrix_data(planner_loc_ids)
        mock_matrix_instance.create_distance_matrix.side_effect = side_effect_create_matrix
        
        mock_solver_instance = MockSolver.return_value
        mock_solver_instance.solve.return_value = mock_opt_result
        
        assignments = planner.plan_assignments()
        self.assertEqual(len(assignments), 0)

    @patch('assignment.services.assignment_planner.ORToolsVRPSolver')
    @patch('assignment.services.assignment_planner.DistanceMatrixBuilder')
    def test_optimizer_route_unknown_vehicle_id(self, MockMatrixBuilder, MockSolver):
        planner = AssignmentPlanner(vehicles=[self.vehicle1], shipments=[self.shipment1])
        
        mock_detailed_route = {"vehicle_id": "UNKNOWN_VEHICLE", "stops": ["loc1", "loc2"]}
        mock_opt_result = OptimizationResult(
            status="success",
            detailed_routes=[mock_detailed_route],
            assigned_vehicles={"UNKNOWN_VEHICLE":0}, statistics={}
        )

        mock_matrix_instance = MockMatrixBuilder.return_value
        def side_effect_create_matrix(*args, **kwargs_matrix):
            planner_loc_ids = [loc.id for loc in kwargs_matrix['locations']]
            return self._get_default_mock_matrix_data(planner_loc_ids)
        mock_matrix_instance.create_distance_matrix.side_effect = side_effect_create_matrix
        
        mock_solver_instance = MockSolver.return_value
        mock_solver_instance.solve.return_value = mock_opt_result
        
        assignments = planner.plan_assignments()
        self.assertEqual(len(assignments), 0)

    @patch('assignment.services.assignment_planner.ORToolsVRPSolver')
    @patch('assignment.services.assignment_planner.DistanceMatrixBuilder')
    def test_depot_stops_without_tasks_do_not_create_items(self, MockMatrixBuilder, MockSolver):
        planner = AssignmentPlanner(vehicles=[self.vehicle1], shipments=[self.shipment1])

        def mock_solve_interaction(*args, **kwargs_solve):
            depot1_actual_id, s1_origin_actual_id = "", ""
            
            for loc_key, loc_dto in planner.location_dto_map.items():
                coords = (loc_dto.latitude, loc_dto.longitude)
                if coords == (self.vehicle1.depot_latitude, self.vehicle1.depot_longitude):
                    depot1_actual_id = loc_dto.id
                elif coords == (float(self.shipment1.origin["lat"]), float(self.shipment1.origin["lng"])):
                    s1_origin_actual_id = loc_dto.id
            
            self.assertTrue(depot1_actual_id and s1_origin_actual_id)
            
            # Simulate only a pickup task for shipment1
            # This modification must happen *before* the planner uses self.optimizer_deliveries
            # for the VRP solve, which is tricky if the mock_solve_interaction is too late.
            # It's better if the test sets up the planner.optimizer_deliveries as needed before calling plan_assignments.
            # However, for this specific test, we are manipulating the *output* of the solver.

            # The solver should only see one task (pickup for shipment1)
            # The planner should set self.optimizer_deliveries to include only the pickup.
            # For this mock, we simulate the solver returns a route with only that task.
            planner.optimizer_deliveries = [
                DeliveryDataclass(
                    id=f"{self.shipment1.id}_pickup", # Use actual shipment ID
                    location_id=s1_origin_actual_id, 
                    demand=float(self.shipment1.demand),
                    is_pickup=True)
            ]
            planner.optimizer_task_to_shipment_role = {
                f"{self.shipment1.id}_pickup": (self.shipment1, "pickup")
            }
            
            mock_detailed_route = {
                "vehicle_id": str(self.vehicle1.vehicle_id),
                "stops": [depot1_actual_id, s1_origin_actual_id, depot1_actual_id],
            }
            return OptimizationResult(
                status="success",
                detailed_routes=[mock_detailed_route],
                assigned_vehicles={str(self.vehicle1.vehicle_id): 0},
                statistics={}
            )

        mock_matrix_instance = MockMatrixBuilder.return_value
        def side_effect_create_matrix(*args, **kwargs_matrix):
            all_loc_dtos = kwargs_matrix['locations']
            planner_loc_ids_str = [loc.id for loc in all_loc_dtos]
            return self._get_default_mock_matrix_data(planner_loc_ids_str)
        mock_matrix_instance.create_distance_matrix.side_effect = side_effect_create_matrix
        
        mock_solver_instance = MockSolver.return_value
        mock_solver_instance.solve.side_effect = mock_solve_interaction
        
        assignments = planner.plan_assignments()
        self.assertEqual(len(assignments), 1)
        assignment = assignments[0]
        
        items = AssignmentItem.objects.filter(assignment=assignment)
        self.assertEqual(items.count(), 1) # Only one item for the pickup task
        self.assertEqual(items[0].shipment, self.shipment1)
        self.assertEqual(items[0].role, "pickup")


    @patch('assignment.services.assignment_planner.ORToolsVRPSolver')
    @patch('assignment.services.assignment_planner.DistanceMatrixBuilder')
    def test_total_load_calculation_multiple_deliveries_on_route(self, MockMatrixBuilder, MockSolver):
        shipment3 = ShipmentModel.objects.create(
            shipment_id="SHIP003", order_id="ORDER003",
            origin={"lat": 6.7, "lng": 79.9}, destination={"lat": 6.8, "lng": 79.95},
            demand=50, status="pending"
        )
        
        planner = AssignmentPlanner(vehicles=[self.vehicle1], shipments=[self.shipment1, shipment3])

        def mock_solve_interaction(*args, **kwargs_solve):
            depot_id, s1_pickup_id, s1_delivery_id, s3_pickup_id, s3_delivery_id = "", "", "", "", ""
            for loc_key, loc_dto in planner.location_dto_map.items():
                coords = (loc_dto.latitude, loc_dto.longitude)
                if coords == (self.vehicle1.depot_latitude, self.vehicle1.depot_longitude): depot_id = loc_dto.id
                elif coords == (float(self.shipment1.origin["lat"]), float(self.shipment1.origin["lng"])): s1_pickup_id = loc_dto.id
                elif coords == (float(self.shipment1.destination["lat"]), float(self.shipment1.destination["lng"])): s1_delivery_id = loc_dto.id
                elif coords == (float(shipment3.origin["lat"]), float(shipment3.origin["lng"])): s3_pickup_id = loc_dto.id
                elif coords == (float(shipment3.destination["lat"]), float(shipment3.destination["lng"])): s3_delivery_id = loc_dto.id
            
            self.assertTrue(all([depot_id, s1_pickup_id, s1_delivery_id, s3_pickup_id, s3_delivery_id]))

            mock_detailed_route = {
                "vehicle_id": str(self.vehicle1.vehicle_id),
                "stops": [depot_id, s1_pickup_id, s3_pickup_id, s1_delivery_id, s3_delivery_id, depot_id],
            }
            return OptimizationResult(
                status="success",
                detailed_routes=[mock_detailed_route],
                assigned_vehicles={str(self.vehicle1.vehicle_id): 0}, statistics={}
            )

        mock_matrix_instance = MockMatrixBuilder.return_value
        def side_effect_create_matrix(*args, **kwargs_matrix):
            all_loc_dtos = kwargs_matrix['locations']
            planner_loc_ids_str = [loc.id for loc in all_loc_dtos]
            return self._get_default_mock_matrix_data(planner_loc_ids_str)
        mock_matrix_instance.create_distance_matrix.side_effect = side_effect_create_matrix
        
        mock_solver_instance = MockSolver.return_value
        mock_solver_instance.solve.side_effect = mock_solve_interaction

        assignments = planner.plan_assignments()
        self.assertEqual(len(assignments), 1)
        assignment = assignments[0]
        
        expected_load = self.shipment1.demand + shipment3.demand
        self.assertEqual(assignment.total_load, expected_load)

        items = AssignmentItem.objects.filter(assignment=assignment).order_by('delivery_sequence')
        self.assertEqual(items.count(), 4)