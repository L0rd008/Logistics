from django.test import TestCase
from rest_framework.test import APIClient
from fleet.models import Vehicle

class VehicleAPITest(TestCase):
    def setUp(self):
        self.client = APIClient()
        Vehicle.objects.create(vehicle_id="TRK001", capacity=100, status="available")
        Vehicle.objects.create(vehicle_id="TRK002", capacity=50, status="maintenance")
        Vehicle.objects.create(vehicle_id="TRK003", capacity=75, status="assigned")

    def test_list_all_vehicles(self):
        response = self.client.get('/api/fleet/vehicles/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 3)

    def test_filter_by_status(self):
        response = self.client.get('/api/fleet/vehicles/?status=available')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['vehicle_id'], 'TRK001')

    def test_filter_by_min_capacity(self):
        response = self.client.get('/api/fleet/vehicles/?min_capacity=80')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['vehicle_id'], 'TRK001')

    def test_filter_by_invalid_capacity(self):
        response = self.client.get('/api/fleet/vehicles/?min_capacity=invalid')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 3)  # fallback to unfiltered

    def test_filter_by_status_and_capacity(self):
        response = self.client.get('/api/fleet/vehicles/?status=assigned&min_capacity=70')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['vehicle_id'], 'TRK003')

    def test_create_vehicle(self):
        payload = {
            'vehicle_id': 'TRK004',
            'capacity': 120,
            'status': 'available'
        }
        response = self.client.post('/api/fleet/vehicles/', payload, format='json')
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data['vehicle_id'], 'TRK004')

    def test_create_vehicle_missing_field(self):
        payload = {
            'capacity': 100
        }
        response = self.client.post('/api/fleet/vehicles/', payload, format='json')
        self.assertEqual(response.status_code, 400)

    def test_create_vehicle_invalid_status(self):
        payload = {
            'vehicle_id': 'TRK005',
            'capacity': 100,
            'status': 'flying'  # not a valid choice
        }
        response = self.client.post('/api/fleet/vehicles/', payload, format='json')
        self.assertEqual(response.status_code, 400)

    def test_update_vehicle_status(self):
        vehicle = Vehicle.objects.get(vehicle_id="TRK001")
        response = self.client.patch(f'/api/fleet/vehicles/{vehicle.id}/', {'status': 'maintenance'}, format='json')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['status'], 'maintenance')

    def test_delete_vehicle(self):
        vehicle = Vehicle.objects.get(vehicle_id="TRK002")
        response = self.client.delete(f'/api/fleet/vehicles/{vehicle.id}/')
        self.assertEqual(response.status_code, 204)
        self.assertFalse(Vehicle.objects.filter(id=vehicle.id).exists())
