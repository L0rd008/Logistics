# Generated by Django 5.2 on 2025-05-05 04:14

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('fleet', '0002_vehicle_created_at_vehicle_current_latitude_and_more'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='fuelrecord',
            name='vehicle',
        ),
        migrations.RemoveField(
            model_name='maintenancerecord',
            name='vehicle',
        ),
        migrations.RemoveField(
            model_name='triprecord',
            name='vehicle',
        ),
        migrations.AddIndex(
            model_name='vehicle',
            index=models.Index(fields=['status'], name='fleet_vehic_status_f5cfd7_idx'),
        ),
        migrations.AddIndex(
            model_name='vehicle',
            index=models.Index(fields=['vehicle_id'], name='fleet_vehic_vehicle_79521d_idx'),
        ),
        migrations.DeleteModel(
            name='FuelRecord',
        ),
        migrations.DeleteModel(
            name='MaintenanceRecord',
        ),
        migrations.DeleteModel(
            name='TripRecord',
        ),
    ]
