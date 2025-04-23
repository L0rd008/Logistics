from django.contrib import admin
from .models import Vehicle

@admin.register(Vehicle)
class VehicleAdmin(admin.ModelAdmin):
    list_display = ('vehicle_id', 'capacity', 'status')
    list_filter = ('status',)
    search_fields = ('vehicle_id',)
