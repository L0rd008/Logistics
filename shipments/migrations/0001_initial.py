# Generated by Django 5.2 on 2025-05-04 13:12

from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='Shipment',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('shipment_id', models.CharField(max_length=32, unique=True)),
                ('order_id', models.CharField(max_length=32)),
                ('origin_warehouse_id', models.CharField(max_length=36)),
                ('destination_warehouse_id', models.CharField(max_length=36)),
                ('status', models.CharField(choices=[('pending', 'Pending'), ('scheduled', 'Scheduled'), ('dispatched', 'Dispatched'), ('in_transit', 'In Transit'), ('delivered', 'Delivered'), ('failed', 'Failed')], default='pending', max_length=20)),
                ('scheduled_dispatch', models.DateTimeField(blank=True, null=True)),
                ('actual_dispatch', models.DateTimeField(blank=True, null=True)),
                ('delivery_time', models.DateTimeField(blank=True, null=True)),
                ('assigned_vehicle_id', models.CharField(blank=True, max_length=36, null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
        ),
    ]
