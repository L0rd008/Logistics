from confluent_kafka import Producer
import json

producer = Producer({'bootstrap.servers': 'localhost:9092'})

event = {
    "order_id": "ORD9999",
    "origin_warehouse_id": "WH001",
    "destination_warehouse_id": "WH002"
}

producer.produce('orders.created', json.dumps(event).encode('utf-8'))
producer.flush()
print("Published mock order event.")
