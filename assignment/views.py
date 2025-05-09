from rest_framework import viewsets, status
from rest_framework.response import Response

from .models.assignment import Assignment
from .models.assignment_item import AssignmentItem
from .serializers import AssignmentSerializer
from fleet.models import Vehicle
from shipments.models import Shipment


class AssignmentViewSet(viewsets.ModelViewSet):
    queryset = Assignment.objects.all()
    serializer_class = AssignmentSerializer

    def create(self, request, *args, **kwargs):
        deliveries = request.data.get("deliveries")
        if not deliveries:
            return Response({"error": "Deliveries required"}, status=400)

        # Calculate total load
        total_load = sum(d.get("load", 0) for d in deliveries)

        # Find an available vehicle that can handle the load
        vehicle = Vehicle.objects.filter(status="available", capacity__gte=total_load).first()
        if not vehicle:
            return Response({"error": "No available vehicle for the load"}, status=400)

        # Update vehicle status
        vehicle.status = "assigned"
        vehicle.save()

        # Create Assignment
        assignment = Assignment.objects.create(
            vehicle=vehicle,
            total_load=total_load,
            status='created'
        )

        # Create AssignmentItem entries
        for delivery in deliveries:
            shipment_id = delivery.get("shipment_id")
            location = delivery.get("location")
            sequence = delivery.get("sequence", 1)
            role = delivery.get("role")

            if role not in ["pickup", "delivery"]:
                return Response({"error": f"Invalid role for shipment {shipment_id}. Must be 'pickup' or 'delivery'."},
                                status=400)

            try:
                shipment = Shipment.objects.get(id=shipment_id)
            except Shipment.DoesNotExist:
                return Response({"error": f"Shipment {shipment_id} does not exist"}, status=400)

            AssignmentItem.objects.create(
                assignment=assignment,
                shipment=shipment,
                delivery_sequence=sequence,
                delivery_location=location,
                role=role
            )

        serializer = self.get_serializer(assignment)
        return Response(serializer.data, status=status.HTTP_201_CREATED)
