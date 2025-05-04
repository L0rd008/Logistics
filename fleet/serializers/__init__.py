from .vehicle import VehicleSerializer, VehicleLocationSerializer

from django.conf import settings

if settings.ENABLE_FLEET_EXTENDED_MODELS:
    from .maintenance import (
        MaintenanceRecordSerializer,
        MaintenanceScheduleSerializer
    )
    from .fuel import FuelRecordSerializer
    from .trip import TripRecordSerializer

    from rest_framework import serializers

    class VehicleDetailSerializer(VehicleSerializer):
        maintenance_records = MaintenanceRecordSerializer(many=True, read_only=True)
        fuel_records = serializers.SerializerMethodField()
        trip_records = serializers.SerializerMethodField()
        location_history = serializers.SerializerMethodField()

        class Meta(VehicleSerializer.Meta):
            fields = VehicleSerializer.Meta.fields + [
                'maintenance_records', 'fuel_records', 'trip_records', 'location_history'
            ]

        def get_fuel_records(self, obj):
            records = obj.fuel_records.all()[:5]
            return FuelRecordSerializer(records, many=True).data

        def get_trip_records(self, obj):
            records = obj.trip_records.all()[:5]
            return TripRecordSerializer(records, many=True).data

        def get_location_history(self, obj):
            records = obj.location_history.all()[:10]
            return VehicleLocationSerializer(records, many=True).data

else:
    class VehicleDetailSerializer(VehicleSerializer):
        """Fallback when extended models are disabled."""
        class Meta(VehicleSerializer.Meta):
            fields = VehicleSerializer.Meta.fields
