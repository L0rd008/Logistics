from django.core.management.base import BaseCommand
from shipments.consumers.order_events import start_order_consumer

class Command(BaseCommand):
    help = 'Start Kafka consumer to listen for orders.created events'

    def handle(self, *args, **kwargs):
        self.stdout.write(self.style.SUCCESS('Starting order consumer...'))
        start_order_consumer()
