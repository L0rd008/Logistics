# Generated by Django 5.2 on 2025-05-07 19:54

from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='DistanceMatrixCache',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('cache_key', models.CharField(max_length=255, unique=True)),
                ('matrix_data', models.TextField()),
                ('location_ids', models.TextField()),
                ('time_matrix_data', models.TextField(blank=True, null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
            ],
            options={
                'verbose_name': 'Distance Matrix Cache',
                'verbose_name_plural': 'Distance Matrix Caches',
                'indexes': [models.Index(fields=['cache_key'], name='route_optim_cache_k_8e6d1d_idx'), models.Index(fields=['created_at'], name='route_optim_created_087bbe_idx')],
            },
        ),
    ]
