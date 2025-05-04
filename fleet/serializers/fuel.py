from rest_framework import serializers
from fleet.models import FuelRecord

class FuelRecordSerializer(serializers.ModelSerializer):
    class Meta:
        model = FuelRecord
        fields = '__all__'
        read_only_fields = ['created_at']
