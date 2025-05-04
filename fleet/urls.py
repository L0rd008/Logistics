from django.urls import path, include
from rest_framework.routers import DefaultRouter
from django.conf import settings

from .views.vehicle import VehicleViewSet
# Note: Only import extended views if enabled

router = DefaultRouter()
router.register(r'vehicles', VehicleViewSet)

if settings.ENABLE_FLEET_EXTENDED_MODELS:
    from .views.maintenance import MaintenanceRecordViewSet
    from .views.fuel import FuelRecordViewSet
    from .views.trip import TripRecordViewSet

    router.register(r'maintenance', MaintenanceRecordViewSet)
    router.register(r'fuel', FuelRecordViewSet)
    router.register(r'trips', TripRecordViewSet)

urlpatterns = [
    path('', include(router.urls)),
]
