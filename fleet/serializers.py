from rest_framework import serializers
from .models import Vehicle, VehicleLocation

from django.conf import settings

if settings.ENABLE_FLEET_EXTENDED_MODELS:
    from fleet.models import MaintenanceRecord, FuelRecord, TripRecord

class VehicleLocationSerializer(serializers.ModelSerializer):
    class Meta:
        model = VehicleLocation
        fields = ['timestamp', 'latitude', 'longitude', 'speed', 'heading']

class VehicleSerializer(serializers.ModelSerializer):
    location_is_stale = serializers.BooleanField(read_only=True)
    is_available = serializers.BooleanField(read_only=True)

    class Meta:
        model = Vehicle
        fields = [
            'id', 'vehicle_id', 'name', 'capacity', 'status', 'fuel_type',
            'plate_number', 'year_of_manufacture', 'current_latitude',
            'current_longitude', 'last_location_update', 'max_speed',
            'fuel_efficiency', 'created_at', 'updated_at', 'is_available',
            'location_is_stale'
        ]
        read_only_fields = ['created_at', 'updated_at', 'last_location_update']

if settings.ENABLE_FLEET_EXTENDED_MODELS:
    from .models import MaintenanceRecord, FuelRecord, TripRecord

    class TripRecordSerializer(serializers.ModelSerializer):
        distance = serializers.IntegerField(read_only=True)
        duration = serializers.FloatField(read_only=True)

        class Meta:
            model = TripRecord
            fields = '__all__'
            read_only_fields = ['created_at', 'updated_at']

    class FuelRecordSerializer(serializers.ModelSerializer):
        class Meta:
            model = FuelRecord
            fields = '__all__'
            read_only_fields = ['created_at']

    class MaintenanceRecordSerializer(serializers.ModelSerializer):
        class Meta:
            model = MaintenanceRecord
            fields = '__all__'
            read_only_fields = ['created_at', 'updated_at']

    class MaintenanceScheduleSerializer(serializers.ModelSerializer):
        vehicle_id = serializers.CharField(source='vehicle.vehicle_id', read_only=True)
        vehicle_name = serializers.CharField(source='vehicle.name', read_only=True)
        days_until_scheduled = serializers.SerializerMethodField()

        class Meta:
            model = MaintenanceRecord
            fields = [
                'id', 'vehicle', 'vehicle_id', 'vehicle_name', 'maintenance_type',
                'status', 'description', 'scheduled_date', 'days_until_scheduled'
            ]

        def get_days_until_scheduled(self, obj):
            from django.utils import timezone
            if obj.scheduled_date:
                today = timezone.now().date()
                delta = obj.scheduled_date - today
                return delta.days
            return None

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
        """Fallback serializer when extended features are disabled."""
        class Meta(VehicleSerializer.Meta):
            fields = VehicleSerializer.Meta.fields
