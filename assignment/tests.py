from django.test import TestCase
from rest_framework.test import APIClient

from assignment.models.assignment import Assignment
from assignment.models.assignment_item import AssignmentItem
from fleet.models import Vehicle
from shipments.models import Shipment


class AssignmentAPITest(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.vehicle = Vehicle.objects.create(vehicle_id="TRK001", capacity=100, status="available")
        self.busy_vehicle = Vehicle.objects.create(vehicle_id="TRK002", capacity=80, status="assigned")
        self.shipment1 = Shipment.objects.create(
            shipment_id="SHP001",
            order_id="ORD001",
            origin={"lat": 6.9, "lng": 79.8},
            destination={"lat": 7.3, "lng": 80.6},
            status="pending"
        )
        self.shipment2 = Shipment.objects.create(
            shipment_id="SHP002",
            order_id="ORD002",
            origin={"lat": 6.9, "lng": 79.8},
            destination={"lat": 7.4, "lng": 80.5},
            status="pending"
        )

    def test_create_assignment_success(self):
        payload = {
            "deliveries": [
                {"shipment_id": self.shipment1.id, "location": {"lat": 7.3, "lng": 80.6}, "load": 40, "sequence": 1},
                {"shipment_id": self.shipment2.id, "location": {"lat": 7.4, "lng": 80.5}, "load": 30, "sequence": 2}
            ]
        }
        response = self.client.post('/api/assignment/assignments/', payload, format='json')
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data['total_load'], 70)
        assignment_id = response.data['id']
        items = AssignmentItem.objects.filter(assignment_id=assignment_id)
        self.assertEqual(items.count(), 2)

    def test_create_assignment_insufficient_capacity(self):
        payload = {
            "deliveries": [
                {"shipment_id": self.shipment1.id, "location": {"lat": 7.3, "lng": 80.6}, "load": 150, "sequence": 1}
            ]
        }
        response = self.client.post('/api/assignment/assignments/', payload, format='json')
        self.assertEqual(response.status_code, 400)
        self.assertIn("No available vehicle", response.data['error'])

    def test_create_assignment_with_no_available_vehicle(self):
        self.vehicle.status = "maintenance"
        self.vehicle.save()
        payload = {
            "deliveries": [
                {"shipment_id": self.shipment1.id, "location": {"lat": 7.3, "lng": 80.6}, "load": 50, "sequence": 1}
            ]
        }
        response = self.client.post('/api/assignment/assignments/', payload, format='json')
        self.assertEqual(response.status_code, 400)

    def test_create_assignment_with_no_deliveries(self):
        payload = {}
        response = self.client.post('/api/assignment/assignments/', payload, format='json')
        self.assertEqual(response.status_code, 400)
        self.assertIn("Deliveries required", response.data['error'])

    def test_get_all_assignments(self):
        assignment = Assignment.objects.create(
            vehicle=self.vehicle,
            total_load=50,
            status='created'
        )
        AssignmentItem.objects.create(
            assignment=assignment,
            shipment=self.shipment1,
            delivery_sequence=1,
            delivery_location={"lat": 7.3, "lng": 80.6}
        )
        response = self.client.get('/api/assignment/assignments/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 1)

    def test_vehicle_marked_assigned_after_assignment(self):
        payload = {
            "deliveries": [
                {"shipment_id": self.shipment1.id, "location": {"lat": 7.3, "lng": 80.6}, "load": 50, "sequence": 1}
            ]
        }
        self.client.post('/api/assignment/assignments/', payload, format='json')
        self.vehicle.refresh_from_db()
        self.assertEqual(self.vehicle.status, "assigned")

    def test_assignment_model_str(self):
        assignment = Assignment.objects.create(
            vehicle=self.vehicle,
            total_load=50,
            status='created'
        )
        expected = f"Assignment #{assignment.id} to Vehicle {self.vehicle.vehicle_id}"
        self.assertEqual(str(assignment), expected)
