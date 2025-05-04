from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.core.exceptions import ValidationError
from django.utils.dateparse import parse_datetime

from .models import Shipment
from .serializers import ShipmentSerializer


class ShipmentViewSet(viewsets.ModelViewSet):
    queryset = Shipment.objects.all()
    serializer_class = ShipmentSerializer
    filterset_fields = ['status', 'order_id', 'origin_warehouse_id', 'destination_warehouse_id']
    search_fields = ['shipment_id', 'order_id']
    ordering_fields = ['created_at', 'scheduled_dispatch']

    def handle_transition(self, request, shipment, transition_func, time_field=None):
        try:
            # If time is required, parse it
            if time_field:
                raw_value = request.data.get(time_field)
                timestamp = parse_datetime(raw_value) if raw_value else None
                transition_func(timestamp)
            else:
                transition_func()
            return Response(self.get_serializer(shipment).data)
        except ValidationError as e:
            return Response({'error': e.message}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['post'])
    def mark_pending(self, request, pk=None):
        shipment = self.get_object()
        return self.handle_transition(request, shipment, shipment.mark_pending)

    @action(detail=True, methods=['post'])
    def mark_scheduled(self, request, pk=None):
        shipment = self.get_object()
        return self.handle_transition(request, shipment, shipment.mark_scheduled, time_field='scheduled_time')

    @action(detail=True, methods=['post'])
    def mark_dispatched(self, request, pk=None):
        shipment = self.get_object()
        return self.handle_transition(request, shipment, shipment.mark_dispatched, time_field='dispatch_time')

    @action(detail=True, methods=['post'])
    def mark_in_transit(self, request, pk=None):
        shipment = self.get_object()
        return self.handle_transition(request, shipment, shipment.mark_in_transit)

    @action(detail=True, methods=['post'])
    def mark_delivered(self, request, pk=None):
        shipment = self.get_object()
        return self.handle_transition(request, shipment, shipment.mark_delivered, time_field='delivery_time')

    @action(detail=True, methods=['post'])
    def mark_failed(self, request, pk=None):
        shipment = self.get_object()
        return self.handle_transition(request, shipment, shipment.mark_failed)
