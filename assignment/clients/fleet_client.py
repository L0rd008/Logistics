from fleet.models import Vehicle


class FleetClient:
    @staticmethod
    def get_available_vehicles(min_capacity=None, limit=None):
        """
        fetch available vehicles, optionally filtered by capacity and limited in count.

        Args:
            min_capacity (int, optional): Minimum vehicle capacity.
            limit (int, optional): Maximum number of vehicles to return.

        Returns:
            QuerySet of Vehicle objects
        """
        qs = Vehicle.objects.filter(status='available')
        if min_capacity is not None:
            qs = qs.filter(capacity__gte=min_capacity)
        if limit is not None:
            qs = qs[:limit]
        return qs

    @staticmethod
    def get_vehicle_by_id(vehicle_id):
        return Vehicle.objects.filter(id=vehicle_id).first()

    @staticmethod
    def mark_assigned(vehicle):
        vehicle.status = 'assigned'
        vehicle.save(update_fields=['status'])
