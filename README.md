# 🚚 Logistics Microservice Suite

This service powers intelligent shipment routing, assignment, fleet matching, and delivery monitoring — driven by Kafka and Django.

---

## 📦 Modules Overview

- **route_optimizer/**: Optimizes delivery routes (independent service)
- **fleet/**: Manages vehicle data and availability
- **assignment/**: Assigns optimized routes to vehicles
- **scheduler/**: Triggers assignment logic periodically (future: Celery/Lambda)
- **monitoring/**: Logs delivery issues, performance (optional)
- **shipments/**: Manages shipment lifecycle
- **map_service/** *(optional)*: Calculates real-world distances via OpenRouteService or dummy matrix

## 🚀 Getting Started

### 🐳 Option A: Run with Docker (Recommended)

#### 1. Clone the Repo

```bash
git clone https://github.com/IASSCMS/Logistics.git
cd Logistics
````

#### 2. Create `.env` File

```env
# .env
DJANGO_PORT=8000
KAFKA_BROKER_URL=kafka:9092
LOGISTICS_SERVICE_PORT=8002
```

#### 3. Start All Services

```bash
docker-compose up --build
```

This spins up:

* Django app
* Kafka + Zookeeper

#### 4. Visit in Browser

* Swagger docs: [http://localhost:8002/swagger/](http://localhost:8002/swagger/)
* Admin panel: [http://localhost:8002/admin/](http://localhost:8002/admin/)

#### 5. Run Django Tests in Docker

```bash
docker-compose run --rm logistics-service python manage.py test
```

---

### 🐍 Option B: Local Dev Setup (Without Docker)

#### 1. Create & Activate Virtual Environment

```bash
python3 -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
```

#### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

#### 3. Setup Environment

Set these in `.env` or shell:

```env
KAFKA_BROKER_URL=localhost:9092
```

#### 4. Run Migrations

```bash
python manage.py migrate
```

#### 5. Start Django Server

```bash
python manage.py runserver
```

---

## 📬 Kafka Setup Notes

This app connects to Kafka topic `orders.created` via `kafka-python`.
Kafka is provided via `confluentinc/cp-kafka` in `docker-compose.yml`.

* Send test events using `publish_mock_event.py`
* Consumer listens via `shipments.consumers.order_events`

---

## 📂 Project Structure

```
logistics/
├── logistics_core/       # Django project
├── fleet/                # Vehicle models & APIs
├── shipments/            # Shipment status, tracking
├── assignment/           # Route-to-vehicle mapping
├── monitoring/           # Logs, dashboard, alerts
├── route_optimizer/      # Standalone optimization engine
├── manage.py
├── Dockerfile
├── entrypoint.sh
├── docker-compose.yml
└── requirements.txt
```

---

## 📄 API Documentation

Once server is running:

* Swagger UI: [http://localhost:8002/swagger/](http://localhost:8002/swagger/)
* Redoc: [http://localhost:8002/redoc/](http://localhost:8002/redoc/)

---

## 🔐 Admin Account

Create one manually:

```bash
python manage.py createsuperuser
```

Or inside Docker:

```bash
docker-compose exec logistics-service python manage.py createsuperuser
```

---
