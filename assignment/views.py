from rest_framework import viewsets, status
from rest_framework.response import Response
from .models import Assignment
from .serializers import AssignmentSerializer
from fleet.models import Vehicle

class AssignmentViewSet(viewsets.ModelViewSet):
    queryset = Assignment.objects.all()
    serializer_class = AssignmentSerializer

    def create(self, request, *args, **kwargs):
        deliveries = request.data.get("deliveries")
        if not deliveries:
            return Response({"error": "Deliveries required"}, status=400)

        total_load = sum(d.get("load", 0) for d in deliveries)
        vehicle = Vehicle.objects.filter(status="available", capacity__gte=total_load).first()
        if not vehicle:
            return Response({"error": "No available vehicle for the load"}, status=400)

        vehicle.status = "assigned"
        vehicle.save()

        assignment = Assignment.objects.create(
            vehicle=vehicle,
            delivery_locations=[d["location"] for d in deliveries],
            total_load=total_load
        )
        serializer = self.get_serializer(assignment)
        return Response(serializer.data, status=status.HTTP_201_CREATED)
