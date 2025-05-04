from django.contrib import admin
from .models import Shipment

@admin.register(Shipment)
class ShipmentAdmin(admin.ModelAdmin):
    list_display = ('shipment_id', 'order_id', 'origin_warehouse_id', 'destination_warehouse_id', 'status', 'created_at')
    list_filter = ('status', 'origin_warehouse_id', 'destination_warehouse_id')
    search_fields = ('shipment_id', 'order_id')
    ordering = ('-created_at',)
