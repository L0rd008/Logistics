from django.urls import reverse
from rest_framework.test import APITestCase
from rest_framework import status

from fleet.models import Vehicle
from shipments.models import Shipment
from assignment.models.assignment import Assignment
from assignment.models.assignment_item import AssignmentItem


class AssignmentAPITests(APITestCase):
    def setUp(self):
        self.vehicle = Vehicle.objects.create(
            vehicle_id="TRK001",
            name="Truck 1",
            capacity=1000,
            status="available",
            fuel_type="diesel"
        )

        self.shipment = Shipment.objects.create(
            order_id="ORD001",
            demand=500,
            origin={"lat": 7.2, "lng": 80.1},
            destination={"lat": 7.3, "lng": 80.2},
            status="pending"
        )

        self.create_url = reverse("assignment-list")  # Default DRF route for create
        self.by_vehicle_url = lambda v_id: reverse("assignment-by-vehicle", kwargs={"vehicle_id": v_id})

    def test_create_assignment(self):
        payload = {
            "deliveries": [
                {
                    "shipment_id": self.shipment.id,
                    "location": {"lat": 7.2, "lng": 80.1},
                    "sequence": 1,
                    "load": 500,
                    "role": "pickup"
                },
                {
                    "shipment_id": self.shipment.id,
                    "location": {"lat": 7.3, "lng": 80.2},
                    "sequence": 2,
                    "load": 0,
                    "role": "delivery"
                }
            ]
        }

        response = self.client.post(self.create_url, payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Assignment.objects.count(), 1)
        self.assertEqual(AssignmentItem.objects.count(), 2)

        assignment = Assignment.objects.first()
        self.assertEqual(assignment.vehicle.vehicle_id, "TRK001")
        self.assertEqual(assignment.total_load, 500)

    def test_get_assignment_by_vehicle(self):
        # First create assignment
        assignment = Assignment.objects.create(
            vehicle=self.vehicle,
            total_load=500,
            status="created"
        )
        AssignmentItem.objects.create(
            assignment=assignment,
            shipment=self.shipment,
            delivery_sequence=1,
            delivery_location={"lat": 7.2, "lng": 80.1},
            role="pickup"
        )

        response = self.client.get(self.by_vehicle_url("TRK001"))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["vehicle"], self.vehicle.vehicle_id)
        self.assertEqual(len(response.data["items"]), 1)
