from django.db import models

from assignment.models.assignment import Assignment
from shipments.models import Shipment


class AssignmentItem(models.Model):
    assignment = models.ForeignKey(Assignment, on_delete=models.CASCADE, related_name='items')
    shipment = models.ForeignKey(Shipment, on_delete=models.CASCADE)
    delivery_sequence = models.PositiveIntegerField()  # 1st, 2nd, 3rd drop, etc.
    delivery_location = models.JSONField()  # { "lat": ..., "lng": ... }

    is_delivered = models.BooleanField(default=False)
    delivered_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['delivery_sequence']

    def __str__(self):
        return f"Shipment {self.shipment.id} in Assignment {self.assignment.id}"
