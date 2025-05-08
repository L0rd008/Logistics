from django.test import TestCase
from shipments.models import Shipment
from shipments.consumers.order_events import handle_order_created


class KafkaConsumerRobustTest(TestCase):
    def test_valid_order_event_creates_shipment(self):
        event = {
            "order_id": "ORD001",
            "origin": {"lat": 6.9271, "lng": 79.8612},
            "destination": {"lat": 7.2906, "lng": 80.6337}
        }
        handle_order_created(event)

        shipment = Shipment.objects.get(order_id="ORD001")
        self.assertEqual(shipment.status, "pending")
        self.assertEqual(shipment.origin, {"lat": 6.9271, "lng": 79.8612})
        self.assertEqual(shipment.destination, {"lat": 7.2906, "lng": 80.6337})

    def test_missing_order_id_does_not_create_shipment(self):
        event = {
            "origin": {"lat": 6.9271, "lng": 79.8612},
            "destination": {"lat": 7.2906, "lng": 80.6337}
        }
        handle_order_created(event)
        self.assertEqual(Shipment.objects.count(), 0)

    def test_missing_origin_does_not_create_shipment(self):
        event = {
            "order_id": "ORD002",
            "destination": {"lat": 7.2906, "lng": 80.6337}
        }
        handle_order_created(event)
        self.assertEqual(Shipment.objects.count(), 0)

    def test_missing_destination_does_not_create_shipment(self):
        event = {
            "order_id": "ORD003",
            "origin": {"lat": 6.9271, "lng": 79.8612}
        }
        handle_order_created(event)
        self.assertEqual(Shipment.objects.count(), 0)

    def test_invalid_data_type_ignored(self):
        event = {
            "order_id": 12345,  # Still acceptable as string-like
            "origin": {"lat": 6.9, "lng": 79.8},
            "destination": {"lat": 7.3, "lng": 80.6}
        }
        handle_order_created(event)
        self.assertEqual(Shipment.objects.filter(order_id=12345).count(), 1)

    def test_duplicate_order_id_creates_separate_shipments(self):
        event = {
            "order_id": "ORDDUP",
            "origin": {"lat": 6.9, "lng": 79.8},
            "destination": {"lat": 7.3, "lng": 80.6}
        }
        handle_order_created(event)
        handle_order_created(event)
        self.assertEqual(Shipment.objects.filter(order_id="ORDDUP").count(), 2)

    def test_extra_fields_are_ignored(self):
        event = {
            "order_id": "ORD004",
            "origin": {"lat": 6.9, "lng": 79.8},
            "destination": {"lat": 7.3, "lng": 80.6},
            "customer_priority": "high",
            "notes": "ignored field"
        }
        handle_order_created(event)
        self.assertTrue(Shipment.objects.filter(order_id="ORD004").exists())

    def test_empty_event_dict(self):
        handle_order_created({})
        self.assertEqual(Shipment.objects.count(), 0)

    def test_null_values(self):
        event = {
            "order_id": None,
            "origin": None,
            "destination": None,
        }
        handle_order_created(event)
        self.assertEqual(Shipment.objects.count(), 0)
