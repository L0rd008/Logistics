Okay, this is a great next step! We'll create a detailed set of integration proposals for each target module. This will serve as a blueprint for refactoring and enhancing the `Logistics` suite by leveraging the full capabilities of the `route_optimizer`.

Here are the detailed integration proposals:

## `route_optimizer` Integration Proposals for the Logistics Suite

This document outlines specific integration points where other modules within the `Logistics` microservice suite can leverage the functionalities of the `route_optimizer` module. The goal is to enhance efficiency, consistency, and accuracy across the platform.

---

### 1. Module: `map_service/`

*   **Context**: The main [Logistics README.md](file:///M:\Documents\Logistics\README.md) describes `map_service/` as "(optional): Calculates real-world distances via OpenRouteService or dummy matrix." This functionality was also noted in our discussion about its potential redundancy on May 19, 2025.

*   **Integration Point 1: Complete Replacement of Distance/Time Calculation**
    *   **Module & File(s) Affected**: The entire `map_service/` module and any files in other modules that import from or call `map_service/`.
    *   **Current Logic**: `map_service/` likely provides functions that take pairs of coordinates (or location identifiers) and return distance and/or travel time, potentially by calling OpenRouteService or using a simple calculation (e.g., Haversine for a "dummy matrix").
    *   **Proposed `route_optimizer` Solution**:
        *   Utilize `route_optimizer.core.distance_matrix.DistanceMatrixBuilder` and its `create_distance_matrix(...)` method.
    *   **Data Mapping Required**:
        *   Any calling module will need to convert its location representations (e.g., raw coordinates, custom location objects) into a list of `route_optimizer.core.types_1.Location` DTOs.
        *   The `DistanceMatrixBuilder` will return a tuple containing the distance matrix (NumPy array in kilometers), an optional time matrix (NumPy array in minutes), and a list of location IDs in the order they appear in the matrices.
    *   **Benefits**:
        *   **Centralization**: Consolidates all distance/time matrix generation into a single, robust component.
        *   **Advanced Features**: Leverages `DistanceMatrixBuilder`'s capabilities:
            *   Google Maps API integration for precise, real-world data (if `GOOGLE_MAPS_API_KEY` is configured in [Logistics\route\_optimizer\settings.py](file:///Logistics\route_optimizer\settings.py)).
            *   Caching of API results via `route_optimizer.models.base.DistanceMatrixCache` (as defined in [Logistics\route\_optimizer\models\base.py](file:///Logistics\route_optimizer\models\base.py)) to reduce costs and latency.
            *   Fallback to local Haversine calculations if API fails or is not configured.
            *   Matrix sanitization (handling `NaN`, `inf`, negative values).
            *   Standardized units (kilometers for distance, minutes for time).
        *   **Code Reduction**: Eliminates the redundant `map_service/` module.
        *   **Consistency**: Ensures all parts of the application use the same source and methodology for distance/time calculations.
    *   **Estimated Complexity**:
        *   **Medium to High** (depending on how many other modules use `map_service/` and the complexity of their current interactions with it). The main effort is in identifying all call sites and refactoring them.

---

### 2. Module: `fleet/`

*   **Context**: The `fleet/` module "Manages vehicle data and availability" ([Logistics README.md](file:///M:\Documents\Logistics\README.md)). It defines a `Vehicle` model in [Logistics\fleet\models\core.py](file:///M:\Documents\Logistics\fleet\models\core.py).

*   **Integration Point 2.1: Service Area / Range Feasibility Check**
    *   **Module & File(s) Affected**: Potentially new service functions within `fleet/services/` or utility functions used by `fleet/` administration views/logic.
    *   **Current Logic (Hypothetical)**: The `fleet` module might currently have no automated way to check if a vehicle, based on its depot location and `max_distance` (if such an attribute exists on the `fleet.models.Vehicle`), can realistically service a set of key customer locations or a defined geographical zone. Manual checks or very simple radius calculations might be used.
    *   **Proposed `route_optimizer` Solution**:
        1.  **Basic Reachability**: Use `route_optimizer.core.distance_matrix.DistanceMatrixBuilder.create_distance_matrix()` to get distances from the vehicle's depot to a list of representative points in the target service area. Compare these distances against a vehicle's operational range.
        2.  **Advanced Feasibility (Operational Simulation)**: Use `route_optimizer.services.optimization_service.OptimizationService.optimize_routes()`. Create a hypothetical scenario with the specific vehicle and a set of "test" deliveries representing the target service area. Constrain by vehicle capacity and its `max_distance` (from `route_optimizer.models.base.Vehicle` dataclass). If a successful `OptimizationResult` is returned with these deliveries assigned, the area is serviceable by that vehicle under those constraints.
    *   **Data Mapping Required**:
        *   `fleet.models.Vehicle` attributes (especially depot coordinates, capacity, max\_distance if available) need to be mapped to `route_optimizer.models.base.Vehicle` dataclass.
        *   Service area points/customer locations need to be mapped to `route_optimizer.core.types_1.Location` DTOs.
    *   **Benefits**:
        *   **Data-Driven Decisions**: Provides accurate, data-driven assessments of vehicle serviceability.
        *   **Realistic Scenarios**: Using `OptimizationService` simulates actual routing constraints for higher accuracy.
    *   **Estimated Complexity**: **Medium**. Involves creating new service logic and mapping data.

*   **Integration Point 2.2: Vehicle Location Updates & ETA to Next Stop/Depot**
    *   **Module & File(s) Affected**: Logic within `fleet/` that processes real-time vehicle location updates (e.g., from GPS trackers).
    *   **Current Logic (Hypothetical)**: If `fleet/` receives vehicle coordinates, it might calculate straight-line distances to the next stop or depot, or it might not have sophisticated ETA calculation.
    *   **Proposed `route_optimizer` Solution**:
        1.  **Distance/Time to Specific Point**:
            *   Use `route_optimizer.core.distance_matrix.DistanceMatrixBuilder.create_distance_matrix()` with the vehicle's current location and the target location (next stop, depot) as inputs. This provides distance and, if API is used, travel time.
        2.  **Path-Based ETA (More Accurate)**:
            *   If a road graph representation is available (e.g., potentially generated by `route_optimizer.services.traffic_service.TrafficService.create_road_graph()` based on API data, though `TrafficService` itself is not fully detailed in current context), use `route_optimizer.core.dijkstra.DijkstraPathFinder.calculate_shortest_path()` to get the actual path and distance/time along roads.
        3.  **Trigger Rerouting**: If the vehicle is significantly off-route or delayed (determined by comparing current location/ETA with the planned route from `assignment`), the `fleet` module (or `monitoring`) could trigger a call to `route_optimizer.services.rerouting_service.ReroutingService`.
    *   **Data Mapping Required**:
        *   Vehicle's current GPS coordinates: Map to a `route_optimizer.core.types_1.Location` DTO.
        *   Next stop/depot coordinates: Map to a `route_optimizer.core.types_1.Location` DTO.
        *   Planned route information (from `AssignmentItem` or `OptimizationResult.detailed_routes`) would be needed for comparison.
    *   **Benefits**:
        *   **More Accurate ETAs**: Using `DistanceMatrixBuilder` (especially with API) or `DijkstraPathFinder` provides better ETAs than simple calculations.
        *   **Proactive Rerouting**: Enables integration with `ReroutingService` for dynamic adjustments.
    *   **Estimated Complexity**: **Medium**. Requires handling real-time data and integrating with multiple `route_optimizer` components.

*   **Integration Point 2.3: Predictive Maintenance Scheduling**
    *   **Module & File(s) Affected**: Logic within `fleet/` related to vehicle maintenance.
    *   **Current Logic (Hypothetical)**: Maintenance might be based on fixed time intervals or manually tracked mileage.
    *   **Proposed `route_optimizer` Solution**:
        *   After routes are planned by the `assignment` module (which uses `route_optimizer`), the `route_optimizer.core.types_1.OptimizationResult` contains `detailed_routes`. Each `route_optimizer.core.types_1.DetailedRoute` object within this list has a `total_distance`.
        *   The `fleet` module can consume these `OptimizationResult` objects (or just the relevant `total_distance` per vehicle per assignment) and aggregate the projected mileage for each physical vehicle (`fleet.models.Vehicle`).
        *   This aggregated projected mileage can then be used to trigger maintenance alerts or schedules.
    *   **Data Mapping Required**:
        *   `route_optimizer.core.types_1.DetailedRoute.vehicle_id` needs to be reliably mapped back to the `fleet.models.Vehicle.vehicle_id`.
        *   The `fleet` module needs a mechanism to store and update accumulated projected mileage for each vehicle.
    *   **Benefits**:
        *   **Proactive Maintenance**: Allows for maintenance based on actual projected usage rather than just time.
        *   **Optimized Vehicle Uptime**: Helps in scheduling maintenance more effectively.
    *   **Estimated Complexity**: **Medium**. Requires data flow from `assignment` to `fleet` and new logic in `fleet` for mileage aggregation.

---

### 3. Module: `logistics_core/`

*   **Context**: A general-purpose module for shared utilities. Specific files are not detailed, but it's a common place for potentially redundant helper functions. The memory from May 14, 2025, about consolidating helper functions is relevant here.

*   **Integration Point 3.1: Replace Custom Distance/Time Utilities**
    *   **Module & File(s) Affected**: Any utility files within `logistics_core/` that contain functions for:
        *   Calculating Haversine distance.
        *   Other geometric distance calculations.
        *   Basic travel time estimations based on distance and average speed.
    *   **Current Logic (Hypothetical)**: Custom implementations of these calculations.
    *   **Proposed `route_optimizer` Solution**:
        *   For Haversine distance: Standardize on `route_optimizer.utils.helpers.haversine_distance` (from [Logistics\route\_optimizer\utils\helpers.py](file:///Logistics\route_optimizer\utils\helpers.py)) if it's maintained as the canonical version. However, for consistency, encouraging the use of `DistanceMatrixBuilder` even for single pairs (by creating `Location` DTOs) might be better if `DistanceMatrixBuilder` is optimized for it or if a specific point-to-point method is added to it.
        *   For more accurate distance/time or matrix calculations: Always use `route_optimizer.core.distance_matrix.DistanceMatrixBuilder.create_distance_matrix()`.
    *   **Data Mapping Required**:
        *   Input coordinates/locations must be mapped to arguments expected by `haversine_distance` or to `route_optimizer.core.types_1.Location` DTOs for `DistanceMatrixBuilder`.
    *   **Benefits**:
        *   **Single Source of Truth**: Eliminates redundant implementations, reducing bugs and maintenance.
        *   **Consistency**: Ensures all parts of the system use the same calculation methods and units.
        *   **Leverage Advanced Features**: Indirectly allows even simple utility callers to benefit from `DistanceMatrixBuilder`'s caching/API integration if they switch to using it.
    *   **Estimated Complexity**: **Low to Medium**. Depends on the number of custom utility functions and their usage across the codebase.

*   **Integration Point 3.2: Standardize Location Representation for Shared Services**
    *   **Module & File(s) Affected**: Any shared services or data structures in `logistics_core/` that deal with geographical locations.
    *   **Current Logic (Hypothetical)**: `logistics_core/` might define its own `Location` class or use simple tuples/dictionaries for coordinates.
    *   **Proposed `route_optimizer` Solution**:
        *   Promote the use of `route_optimizer.core.types_1.Location` DTO as the standard representation for geographical points with associated attributes (like service times, time windows) when interacting with any service that ultimately might feed into or use `route_optimizer`.
    *   **Data Mapping Required**:
        *   Develop clear conventions or utility functions for converting between `logistics_core`'s location representation (if any) and `route_optimizer.core.types_1.Location` DTO.
    *   **Benefits**:
        *   **Interoperability**: Simplifies data exchange between `logistics_core` utilities and `route_optimizer`.
        *   **Clarity and Type Safety**: `Location` DTO provides a well-defined, type-safe structure.
    *   **Estimated Complexity**: **Low**. Primarily involves agreeing on conventions and potentially writing simple adapter functions.

---

### 4. Module: `shipments/`

*   **Context**: Manages the shipment lifecycle ([Logistics README.md](file:///M:\Documents\Logistics\README.md)). A consumer like `shipments.consumers.order_events` (mentioned in past chat) processes incoming orders.

*   **Integration Point 4.1: Early Feasibility/ETA Estimation on Order Ingestion**
    *   **Module & File(s) Affected**: `shipments.consumers.order_events` or any service called by it upon receiving a new shipment order.
    *   **Current Logic (Hypothetical)**: May perform very basic checks (e.g., if destination is within a wide predefined zone) or provide no immediate ETA/feasibility feedback.
    *   **Proposed `route_optimizer` Solution**:
        *   Use `route_optimizer.services.optimization_service.OptimizationService.optimize_routes()`.
        *   **Scenario**: When a new shipment is created:
            1.  Fetch relevant existing active routes/assignments (if any, potentially from the `assignment` module's state).
            2.  Convert the new shipment into a `route_optimizer.models.base.Delivery` dataclass.
            3.  Convert relevant vehicle data into `route_optimizer.models.base.Vehicle` dataclasses.
            4.  Convert all relevant locations (depots, new shipment origin/destination, existing stops on active routes) into `route_optimizer.core.types_1.Location` DTOs.
            5.  Call `optimize_routes()` with the new shipment added to the list of deliveries. This could be a "what-if" call, possibly with a short solver time limit or simplified constraints, to see if the new shipment can be integrated.
        *   The `OptimizationResult` can indicate:
            *   If the new shipment is `unassigned_deliveries`, it might be infeasible with current constraints.
            *   If assigned, `detailed_routes` would contain its planned path and estimated arrival times.
    *   **Data Mapping Required**:
        *   New `ShipmentModel` data (origin/destination coordinates, demand, priority) to `route_optimizer.models.base.Delivery` dataclass and associated `route_optimizer.core.types_1.Location` DTOs.
        *   Data for currently active vehicles/routes needs to be mapped to `route_optimizer` DTOs/dataclasses.
    *   **Benefits**:
        *   **Early Feedback**: Provides (potentially rough) feasibility and ETA information to customers or operators early in the process.
        *   **Better Planning**: Allows for more dynamic integration of new orders.
    *   **Caveats**: Calling full optimization for every new shipment in real-time can be resource-intensive. Batching new shipments for such "what-if" analysis or using simplified heuristics first might be necessary.
    *   **Estimated Complexity**: **High**. Requires careful state management of current routes/assignments, complex data mapping, and performance considerations for the "what-if" optimization calls.

*   **Integration Point 4.2: Replace Custom Proximity-Based Batching/Grouping**
    *   **Module & File(s) Affected**: Any logic in `shipments/` that attempts to pre-group shipments before sending them to the `assignment` module for detailed planning.
    *   **Current Logic (Hypothetical)**: May use simple distance calculations (e.g., shipments within X km of each other) to form initial batches.
    *   **Proposed `route_optimizer` Solution**:
        *   The primary grouping/batching is inherently handled by `route_optimizer.core.ortools_optimizer.ORToolsVRPSolver` when it constructs optimal multi-stop routes. For most cases, sending individual (or minimally processed) `Delivery` dataclasses to `OptimizationService` (via `AssignmentPlanner`) is the best approach.
        *   If some form of pre-grouping is still strictly required for business reasons (e.g., assigning shipments to predefined zones before detailed routing within zones):
            *   Use `route_optimizer.core.distance_matrix.DistanceMatrixBuilder.create_distance_matrix()` to get accurate distances between all shipment locations or between shipments and zone centers. This data can then feed into the custom zoning/batching logic.
    *   **Data Mapping Required**:
        *   Shipment locations to `route_optimizer.core.types_1.Location` DTOs.
    *   **Benefits**:
        *   **Optimal Grouping**: Relies on the sophisticated VRP solver for true optimal batching (route construction).
        *   **Accuracy**: If pre-grouping is still done, uses accurate distances from `DistanceMatrixBuilder`.
    *   **Estimated Complexity**: **Low to Medium**. Mostly involves removing custom batching logic or refining it to use `DistanceMatrixBuilder` outputs.

---

### 5. Module: `monitoring/`

*   **Context**: "Logs delivery issues, performance (optional)" ([Logistics README.md](file:///M:\Documents\Logistics\README.md)).

*   **Integration Point 5.1: Impact Assessment of Real-Time Events (Delays, Traffic)**
    *   **Module & File(s) Affected**: Services within `monitoring/` that process real-time event data (e.g., from Kafka, vehicle trackers, manual reports).
    *   **Current Logic (Hypothetical)**: May simply log the event or perform basic alerts.
    *   **Proposed `route_optimizer` Solution**:
        *   When `monitoring/` detects a significant event (e.g., major traffic jam reported, vehicle reports long delay at a customer):
            *   Trigger a call to `route_optimizer.services.rerouting_service.ReroutingService`.
                *   `reroute_for_traffic()`: Provide new `traffic_data`.
                *   `reroute_for_delay()`: Provide `delayed_location_ids` and `delay_minutes`.
                *   `reroute_for_roadblock()`: Provide `blocked_segments`.
        *   The `ReroutingService` will use `OptimizationService` to re-plan affected routes. The new `OptimizationResult` will contain updated ETAs, routes, and `ReroutingInfo` in its statistics.
    *   **Data Mapping Required**:
        *   Event data from `monitoring/` (e.g., affected locations, delay durations, traffic segment details, roadblock locations) needs to be translated into the input parameters of the `ReroutingService` methods (e.g., `Location` DTOs, `traffic_data` dictionary, `blocked_segments` list of tuples).
        *   The current route plan (`OptimizationResult` DTO), list of all relevant locations, vehicles, original deliveries, and completed deliveries for the affected route(s) must be fetched (likely from `assignment` or a central data store) and passed to the `ReroutingService`.
        *   The `ReroutingRequestSerializer` ([Logistics\route\_optimizer\api\serializers.py](file:///M:\Documents\Logistics\route_optimizer\api\serializers.py)) gives a good indication of the data structure expected by the rerouting views, which mirrors the service layer's needs.
    *   **Benefits**:
        *   **Proactive Adjustments**: Enables the system to react to real-world events and update plans dynamically.
        *   **Improved Accuracy**: Provides more realistic ETAs and plans after disruptions.
        *   **Informed Decision Making**: Gives operators an updated plan to manage exceptions.
    *   **Estimated Complexity**: **High**. Requires robust event processing, fetching current operational state, complex data mapping, and invoking rerouting which is computationally intensive.

*   **Integration Point 5.2: Route Deviation Analysis & Correction Aid**
    *   **Module & File(s) Affected**: Logic in `monitoring/` that compares actual vehicle locations against planned routes.
    *   **Current Logic (Hypothetical)**: May raise an alert if a vehicle is X distance off its planned path.
    *   **Proposed `route_optimizer` Solution**:
        1.  **Distance to Planned Path/Next Stop**:
            *   Use `route_optimizer.core.distance_matrix.DistanceMatrixBuilder.create_distance_matrix()` with the vehicle's current location and its next few planned stops (from `OptimizationResult.detailed_routes`) to quantify the deviation.
        2.  **Shortest Path to Rejoin/Proceed**:
            *   If a road graph is available, use `route_optimizer.core.dijkstra.DijkstraPathFinder.calculate_shortest_path()` to find the best way for the deviated vehicle to rejoin its original route or proceed to the next planned stop.
        3.  **Full Reroute for Severe Deviations**:
            *   If the deviation is significant or makes the original plan untenable, trigger `route_optimizer.services.rerouting_service.ReroutingService` as described in 5.1, treating the vehicle's current location as its new starting point for re-optimization.
    *   **Data Mapping Required**:
        *   Vehicle's current GPS coordinates to a `route_optimizer.core.types_1.Location` DTO.
        *   Planned route data (`OptimizationResult.detailed_routes`) from the `assignment` module.
    *   **Benefits**:
        *   **Intelligent Deviation Handling**: Goes beyond simple alerts to provide data for corrective action.
        *   **Efficiency**: Helps find the best way to recover from deviations.
    *   **Estimated Complexity**: **Medium to High**. Depends on the sophistication of deviation detection and the chosen correction strategy (from simple distance checks to full rerouting).

*   **Integration Point 5.3: Performance Analysis (Planned vs. Actual)**
    *   **Module & File(s) Affected**: Reporting or analytics components within `monitoring/`.
    *   **Current Logic (Hypothetical)**: May track actual completion times but not compare them systematically against planned values.
    *   **Proposed `route_optimizer` Solution**:
        *   `monitoring/` should collect actual data (travel times, distances driven, service times, completion times).
        *   Compare this actual data against the planned values stored in:
            *   `route_optimizer.core.types_1.OptimizationResult.statistics` (e.g., `total_distance`, `total_time`, populated by `RouteStatsService`).
            *   `route_optimizer.core.types_1.DetailedRoute` attributes (e.g., `segments[*].distance_km`, `segments[*].time_minutes`, `estimated_arrival_time_at_stops`).
    *   **Data Mapping Required**:
        *   A clear way to link actual events/telemetry back to specific planned routes, segments, and stops from the `OptimizationResult`.
    *   **Benefits**:
        *   **Performance Benchmarking**: Quantifies the accuracy of the optimizer and operational efficiency.
        *   **Identifies Bottlenecks**: Highlights areas where plans consistently differ from reality.
        *   **Continuous Improvement**: Data can be used to refine optimizer parameters or operational procedures.
    *   **Estimated Complexity**: **Medium**. Requires robust data collection for actuals and a good system for matching planned vs. actual data.

---

### 6. Module: `assignment/`

*   **Context**: Assigns optimized routes to vehicles. The `AssignmentPlanner` ([Logistics\assignment\services\assignment\_planner.py](file:///M:\Documents\Logistics\assignment\services\assignment_planner.py)) has already been significantly refactored to use `ORToolsVRPSolver` and `DistanceMatrixBuilder` from `route_optimizer` as per our previous discussions and code changes (e.g., May 19, 2025).

*   **Integration Point 6.1: Pre-Assignment Validation/Filtering (Refinement)**
    *   **Module & File(s) Affected**: [Logistics\assignment\services\assignment_planner.py](file:///M:\Documents\Logistics\assignment\services\assignment_planner.py) or logic that calls it.
    *   **Current Logic**: `AssignmentPlanner` currently proceeds to build inputs for `ORToolsVRPSolver` directly. While it handles missing vehicle depot coordinates, it doesn't have explicit pre-filtering based on broader geographical feasibility before attempting the full VRP solve.
    *   **Proposed `route_optimizer` Solution**:
        *   Before the detailed mapping of all shipments and vehicles, `AssignmentPlanner` *could* perform an optional, quick feasibility check using `route_optimizer.core.distance_matrix.DistanceMatrixBuilder.create_distance_matrix()`.
        *   **Scenario**: For a given batch of shipments, calculate a matrix including all shipment locations and all available vehicle depots. This could identify:
            *   Shipments that are extremely far from *any* depot.
            *   Subsets of shipments that are geographically very isolated from the main cluster.
        *   This pre-check could flag potentially problematic shipments or allow for splitting large, disparate batches into more manageable optimization problems.
    *   **Data Mapping Required**:
        *   `fleet.models.Vehicle.depot_latitude/longitude` to `route_optimizer.core.types_1.Location` DTOs.
        *   `shipments.models.Shipment.origin/destination` to `route_optimizer.core.types_1.Location` DTOs.
    *   **Benefits**:
        *   **Early Problem Detection**: Can identify impossible assignments or suggest batch splitting before a potentially long VRP solve.
        *   **Improved Solver Performance**: For very large and sparse problems, pre-filtering might lead to faster solves for the core, feasible set.
    *   **Estimated Complexity**: **Low to Medium**. Logic for interpreting the pre-check distance matrix and deciding on actions would need to be added.

*   **Integration Point 6.2: Consumption of Enriched `OptimizationResult`**
    *   **Module & File(s) Affected**: [Logistics\assignment\services\assignment_planner.py](file:///M:\Documents\Logistics\assignment\services\assignment_planner.py) where it processes the `OptimizationResult`.
    *   **Current Logic**: The refactored `AssignmentPlanner` processes `OptimizationResult.detailed_routes` to create `Assignment` and `AssignmentItem` objects.
    *   **Proposed `route_optimizer` Solution (Ensure Full Utilization)**:
        *   Ensure `AssignmentPlanner` and any downstream consumers in `assignment` (or other modules like `monitoring`) are aware of and can use all relevant fields from the `OptimizationResult` DTO, including:
            *   `status`
            *   `total_distance`, `total_cost`
            *   `assigned_vehicles`
            *   `unassigned_deliveries` (crucial for handling shipments that couldn't be planned)
            *   `statistics` (which includes outputs from `RouteStatsService` like `used_vehicles`, `assigned_deliveries`, `computation_time_ms`, and potentially `rerouting_info`).
    *   **Data Mapping Required**: Already largely in place due to the refactoring. This is more about ensuring complete data utilization.
    *   **Benefits**:
        *   **Full Visibility**: Makes all optimization output available for decision-making, logging, and further processing.
        *   **Robust Error Handling**: Properly handling `unassigned_deliveries` and error statuses.
    *   **Estimated Complexity**: **Low**. Primarily involves reviewing current result processing logic to ensure no valuable data from `OptimizationResult` is overlooked.

---

**Prioritization Approach:**

1.  **High Priority - Foundational**:
    *   **`map_service/` Replacement (1.1)**: This is a clear win for centralization and leveraging `DistanceMatrixBuilder`'s advanced features.
    *   **`logistics_core/` Distance Utility Replacement (3.1)**: Promotes consistency and reduces redundancy.

2.  **Medium Priority - Core Functional Enhancements**:
    *   **`fleet/` Service Area Check (2.1) & ETA Calculation (2.2)**: Directly enhances `fleet` module's capabilities.
    *   **`monitoring/` Impact Assessment (5.1) & Deviation Analysis (5.2)**: Critical for operational responsiveness.
    *   **`assignment/` Pre-Assignment Validation (6.1) & Full Result Utilization (6.2)**: Refines the already integrated module.

3.  **Lower Priority / More Complex / Future Enhancements**:
    *   **`fleet/` Predictive Maintenance (2.3)**: Valuable but might require more infrastructure.
    *   **`shipments/` Early Feasibility/ETA (4.1)**: High potential value but complex to implement performantly.
    *   **`monitoring/` Performance Analysis (5.3)**: Requires robust actuals data collection.

This detailed breakdown should provide a clear path forward for integrating `route_optimizer` more deeply into your `Logistics` suite. Each point would ideally be broken down into smaller tasks for development and testing.