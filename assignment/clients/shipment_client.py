from shipments.models import Shipment

class ShipmentClient:
    @staticmethod
    def get_pending_shipments():
        return Shipment.objects.filter(status='pending')

    @staticmethod
    def mark_scheduled(shipment, vehicle, dispatch_time=None):
        shipment.status = 'scheduled'
        shipment.assigned_vehicle_id = vehicle.id
        if dispatch_time:
            shipment.scheduled_dispatch = dispatch_time
        shipment.save(update_fields=['status', 'assigned_vehicle_id', 'scheduled_dispatch'])
