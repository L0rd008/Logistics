from django.db.models import QuerySet
from rest_framework.viewsets import ModelViewSet
from .models import Vehicle
from .serializers import VehicleSerializer

class VehicleViewSet(ModelViewSet):
    queryset = Vehicle.objects.all()
    serializer_class = VehicleSerializer

    def get_queryset(self):
        queryset = super().get_queryset()
        request = self.request  # DRF Request, safe to use .query_params

        status = request.query_params.get('status')
        min_capacity = request.query_params.get('min_capacity')

        if status:
            queryset = queryset.filter(status=status)
        if min_capacity:
            try:
                min_capacity = int(min_capacity)
                queryset = queryset.filter(capacity__gte=min_capacity)
            except ValueError:
                pass  # Ignore invalid capacity filters

        return queryset
