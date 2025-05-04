from rest_framework import serializers
from fleet.models import TripRecord

class TripRecordSerializer(serializers.ModelSerializer):
    distance = serializers.IntegerField(read_only=True)
    duration = serializers.FloatField(read_only=True)

    class Meta:
        model = TripRecord
        fields = '__all__'
        read_only_fields = ['created_at', 'updated_at']
