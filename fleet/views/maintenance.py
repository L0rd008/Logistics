import os
import django

from fleet.models import MaintenanceRecord
from fleet.serializers import MaintenanceRecordSerializer, MaintenanceScheduleSerializer

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'logistics_core.settings')
django.setup()
from django.utils import timezone
from rest_framework import viewsets, status, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from datetime import datetime, timedelta


class MaintenanceRecordViewSet(viewsets.ModelViewSet):
    """
    API endpoint for managing maintenance records.
    """
    queryset = MaintenanceRecord.objects.all()
    serializer_class = MaintenanceRecordSerializer
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['vehicle', 'maintenance_type', 'status']
    ordering_fields = ['scheduled_date', 'completion_date', 'created_at']
    ordering = ['-scheduled_date']

    @action(detail=True, methods=['post'])
    def complete(self, request, pk=None):
        """
        Mark maintenance as completed.
        POST /api/fleet/maintenance/{id}/complete/
        """
        maintenance = self.get_object()

        if maintenance.status == 'completed':
            return Response(
                {'error': 'This maintenance is already completed'},
                status=status.HTTP_400_BAD_REQUEST
            )

        completion_date = request.data.get('completion_date')
        cost = request.data.get('cost')

        try:
            if completion_date:
                completion_date = datetime.fromisoformat(completion_date).date()

            if cost:
                cost = float(cost)

            maintenance.complete_maintenance(completion_date, cost)
            return Response(
                MaintenanceRecordSerializer(maintenance).data,
                status=status.HTTP_200_OK
            )
        except ValueError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )

    @action(detail=False, methods=['get'])
    def upcoming(self, request):
        """
        List upcoming maintenance events.
        GET /api/fleet/maintenance/upcoming/
        """
        upcoming = MaintenanceRecord.objects.filter(
            status__in=['scheduled', 'in_progress'],
            scheduled_date__gte=timezone.now().date()
        ).order_by('scheduled_date')

        # Optionally filter by days in the future
        days = request.query_params.get('days')
        if days:
            try:
                days = int(days)
                future_date = timezone.now().date() + timedelta(days=days)
                upcoming = upcoming.filter(scheduled_date__lte=future_date)
            except ValueError:
                pass

        serializer = MaintenanceScheduleSerializer(upcoming, many=True)
        return Response(serializer.data)
