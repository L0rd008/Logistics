# Logistics

- route_optimizer/ (Standalone service)
  - Inputs: delivery locations, vehicle capacities
  - Output: optimized delivery route
  - Purpose: The brain of the logistics module
  - Develop this first so you can test assignment logic early
 
- map_service/ (Optional)
  - Utility/service to fetch real-world distances
  - Can be a local function or API-based (OpenRouteService / OpenStreetMap)
  - Can be skipped initially, use dummy distance matrix
 
- fleet/ (Django app)
  - Models: Vehicle, Status, Capacity, Location
  - REST APIs to get available vehicles, update location/status
  - You’ll need this to match vehicles with optimized route
 
- assignment/ (Django app)
  - Inputs: optimized route + available vehicles (from fleet)
  - Logic: assign deliveries to vehicle
  - Output: assignment events, persisted records
  - Triggers optimizer and manages dispatching
 
- scheduler/ (Lambda or Celery)
  - Automatically triggers assignment + route_optimizer daily/hourly
  - Optional for early dev, but crucial for automation
 
- monitoring/ (Django app)
  - Captures logs, alerts, failed deliveries, delays
  - Optional dashboard with charts and status
  - Could connect with Kafka or DB log events from assignment
 
    
