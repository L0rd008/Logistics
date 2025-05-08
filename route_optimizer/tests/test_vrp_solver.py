import unittest
from route_optimizer.models.vrp_input import VRPInputBuilder, VRPCompiler, Location, Vehicle, DeliveryTask
from route_optimizer.services.vrp_solver import solve_cvrp


class TestSolveCVRP(unittest.TestCase):
    def test_basic_functionality(self):
        # Define locations
        depot = Location(0, 0)
        pickup = Location(1, 0)
        delivery = Location(2, 0)

        # Create vehicle and task
        vehicle = Vehicle(id="V1", depot=depot, capacity=10)
        task = DeliveryTask(id="T1", pickup=pickup, delivery=delivery, demand=5)

        # Build VRP input
        builder = VRPInputBuilder()
        builder.add_vehicle(vehicle)
        builder.add_delivery_task(task)

        # Set distances
        builder.set_distance(0, 1, 10)
        builder.set_distance(1, 2, 10)
        builder.set_distance(2, 0, 10)

        vrp_input = VRPCompiler.compile(builder)

        # Solve CVRP
        result = solve_cvrp(vrp_input)

        # Assertions
        self.assertEqual(result["status"], "success")
        self.assertIn("routes", result)
        self.assertIn("total_distance", result)
        self.assertEqual(len(result["routes"]), 1)
        self.assertEqual(result["total_distance"], 30)
