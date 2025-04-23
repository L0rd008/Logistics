from django.db import models
# from django.contrib.gis.db import models as geomodels  # if using PostGIS

class Vehicle(models.Model):
    STATUS_CHOICES = [
        ('available', 'Available'),
        ('assigned', 'Assigned'),
        ('maintenance', 'Maintenance')
    ]

    vehicle_id = models.CharField(max_length=20, unique=True)
    capacity = models.PositiveIntegerField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='available')
    # current_location = geomodels.PointField(geography=True, null=True, blank=True)  # optional

    def __str__(self):
        return f"{self.vehicle_id} ({self.status})"
