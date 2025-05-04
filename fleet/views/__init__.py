from .vehicle import VehicleViewSet

from django.conf import settings
if settings.ENABLE_FLEET_EXTENDED_MODELS:
    from .maintenance import MaintenanceRecordViewSet
    from .fuel import FuelRecordViewSet
    from .trip import TripRecordViewSet
