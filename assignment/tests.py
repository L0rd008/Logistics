from django.test import TestCase
from rest_framework.test import APIClient
from fleet.models import Vehicle
from .models import Assignment

class AssignmentAPITest(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.vehicle = Vehicle.objects.create(vehicle_id="TRK001", capacity=100, status="available")

    def test_create_assignment_success(self):
        payload = {
            "deliveries": [
                {"location": [77.59, 12.97], "load": 40},
                {"location": [77.61, 12.98], "load": 30}
            ]
        }
        response = self.client.post('/api/assignment/assignments/', payload, format='json')
        self.assertEqual(response.status_code, 201)

    def test_create_assignment_insufficient_capacity(self):
        payload = {
            "deliveries": [
                {"location": [77.59, 12.97], "load": 120}
            ]
        }
        response = self.client.post('/api/assignment/assignments/', payload, format='json')
        self.assertEqual(response.status_code, 400)

    def test_get_assignments(self):
        Assignment.objects.create(
            vehicle=self.vehicle,
            delivery_locations=[[77.59, 12.97], [77.61, 12.98]],
            total_load=70
        )
        response = self.client.get('/api/assignment/assignments/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 1)
