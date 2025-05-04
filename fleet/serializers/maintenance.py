from rest_framework import serializers
from fleet.models import MaintenanceRecord

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
            delta = obj.scheduled_date - timezone.now().date()
            return delta.days
        return None
