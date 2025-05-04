import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'logistics_core.settings')
django.setup()
from django.db.models import Sum, Count
from django.utils import timezone
from rest_framework import viewsets, status, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from datetime import datetime, timedelta

from fleet.models import Vehicle, VehicleLocation, MaintenanceRecord
from fleet.serializers import VehicleSerializer, VehicleDetailSerializer


class VehicleViewSet(viewsets.ModelViewSet):
    """
    API endpoint for managing vehicles.
    """
    queryset = Vehicle.objects.all()
    serializer_class = VehicleSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['status', 'fuel_type']
    search_fields = ['vehicle_id', 'name', 'plate_number']
    ordering_fields = ['vehicle_id', 'capacity', 'status', 'created_at']
    ordering = ['vehicle_id']

    def get_serializer_class(self):
        if self.action == 'retrieve':
            return VehicleDetailSerializer
        return super().get_serializer_class()

    def get_queryset(self):
        queryset = super().get_queryset()
        request = self.request  # DRF Request, safe to use .query_params

        status = request.query_params.get('status')
        min_capacity = request.query_params.get('min_capacity')
        max_capacity = request.query_params.get('max_capacity')
        available_only = request.query_params.get('available') == 'true'

        if status:
            queryset = queryset.filter(status=status)
        if min_capacity:
            try:
                min_capacity = int(min_capacity)
                queryset = queryset.filter(capacity__gte=min_capacity)
            except ValueError:
                pass  # Ignore invalid capacity filters
        if max_capacity:
            try:
                max_capacity = int(max_capacity)
                queryset = queryset.filter(capacity__lte=max_capacity)
            except ValueError:
                pass
        if available_only:
            queryset = queryset.filter(status='available')

        return queryset

    @action(detail=True, methods=['post'])
    def update_location(self, request, pk=None):
        """
        Update vehicle location.
        POST /api/fleet/vehicles/{id}/update_location/
        """
        vehicle = self.get_object()

        # Extract location data from request
        latitude = request.data.get('latitude')
        longitude = request.data.get('longitude')
        speed = request.data.get('speed')
        heading = request.data.get('heading')

        # Validate required fields
        if not latitude or not longitude:
            return Response(
                {'error': 'Latitude and longitude are required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            # Update current location on vehicle
            vehicle.update_location(latitude, longitude)

            # Create a location history record
            location_data = {
                'vehicle': vehicle,
                'latitude': latitude,
                'longitude': longitude
            }

            if speed is not None:
                location_data['speed'] = speed
            if heading is not None:
                location_data['heading'] = heading

            VehicleLocation.objects.create(**location_data)

            return Response({'status': 'location updated'}, status=status.HTTP_200_OK)
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )

    @action(detail=True, methods=['post'])
    def change_status(self, request, pk=None):
        """
        Change vehicle status.
        POST /api/fleet/vehicles/{id}/change_status/
        """
        vehicle = self.get_object()
        new_status = request.data.get('status')

        if not new_status:
            return Response(
                {'error': 'Status is required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Validate status choice
        if new_status not in dict(Vehicle.STATUS_CHOICES):
            return Response(
                {'error': f'Invalid status. Must be one of: {dict(Vehicle.STATUS_CHOICES).keys()}'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Handle status change to maintenance
        if new_status == 'maintenance' and vehicle.status != 'maintenance':
            # Optionally create a maintenance record
            maintenance_type = request.data.get('maintenance_type', 'routine')
            description = request.data.get('description', 'Routine maintenance')
            scheduled_date = request.data.get('scheduled_date', timezone.now().date().isoformat())

            try:
                scheduled_date = datetime.fromisoformat(scheduled_date).date()
            except ValueError:
                scheduled_date = timezone.now().date()

            # Create maintenance record
            MaintenanceRecord.objects.create(
                vehicle=vehicle,
                maintenance_type=maintenance_type,
                description=description,
                scheduled_date=scheduled_date,
                status='in_progress'  # Since we're changing status to maintenance now
            )

        # Update vehicle status
        vehicle.status = new_status
        vehicle.save(update_fields=['status', 'updated_at'])

        return Response(VehicleSerializer(vehicle).data)

    @action(detail=False, methods=['get'])
    def stats(self, request):
        """
        Get fleet statistics.
        GET /api/fleet/vehicles/stats/
        """
        # Count vehicles by status
        status_counts = dict(
            Vehicle.objects.values('status').annotate(count=Count('id')).values_list('status', 'count')
        )

        # Fill in missing statuses with 0
        for status, _ in Vehicle.STATUS_CHOICES:
            if status not in status_counts:
                status_counts[status] = 0

        # Count total vehicles
        total_vehicles = Vehicle.objects.count()

        # Calculate total fleet capacity
        total_capacity = Vehicle.objects.aggregate(Sum('capacity'))['capacity__sum'] or 0

        # Calculate available capacity
        available_capacity = Vehicle.objects.filter(status='available').aggregate(
            Sum('capacity')
        )['capacity__sum'] or 0

        # Calculate maintenance stats
        maintenance_count = MaintenanceRecord.objects.filter(
            status__in=['scheduled', 'in_progress']
        ).count()

        # Current utilization rate
        utilization_rate = 0
        if total_vehicles > 0:
            assigned_count = status_counts.get('assigned', 0)
            utilization_rate = (assigned_count / total_vehicles) * 100

        return Response({
            'total_vehicles': total_vehicles,
            'status_counts': status_counts,
            'total_capacity': total_capacity,
            'available_capacity': available_capacity,
            'maintenance_count': maintenance_count,
            'utilization_rate': utilization_rate
        })
