# models/__init__.py
from logistics_core import settings
from .core import Vehicle, VehicleLocation

if settings.ENABLE_FLEET_EXTENDED_MODELS:
    from .extended_models import FuelRecord, MaintenanceRecord, TripRecord
