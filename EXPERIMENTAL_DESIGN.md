# Experimental Design: MAS-FRO System Evaluation

## Multi-Agent System for Flood Route Optimization (MAS-FRO)

---

## 1. Experimental Objectives

### 1.1 Primary Objectives

The experiments aim to evaluate the MAS-FRO system's performance in dynamically optimizing evacuation routes under varying flood conditions. Specifically, the study seeks to:

1. **Assess Routing Efficiency**: Evaluate computation time and route quality of the Risk-Aware A* algorithm compared to standard baselines.
2. **Validate Risk Assessment Accuracy**: Verify the FEMA-calibrated sigmoid depth-to-risk model against established hydrological standards.
3. **Measure System Responsiveness**: Quantify latency in real-time data updates via WebSocket connections.
4. **Evaluate NLP Pipeline Performance**: Verify accuracy of the ScoutAgent's crowdsourced data processing.
5. **Test Multi-Agent Coordination**: Assess the effectiveness of inter-agent communication via ACL protocol.

### 1.2 Research Questions

| ID | Research Question |
|----|-------------------|
| RQ1 | How does the Risk-Aware A* algorithm compare to standard Dijkstra/A* in terms of route safety and distance overhead? |
| RQ2 | What is the optimal risk penalty value (λ) for balancing safety and route efficiency? |
| RQ3 | How accurately does the FEMA-calibrated sigmoid function predict flood risk from depth measurements? |
| RQ4 | What is the system's end-to-end latency for risk updates from data collection to frontend visualization? |
| RQ5 | How effective is the NLP pipeline in extracting actionable flood information from bilingual social media posts? |

---

## 2. Experimental Setup

### 2.1 Study Area Specification

| Parameter | Value | Source |
|-----------|-------|--------|
| **Location** | Marikina City, Philippines | Geographic selection |
| **Selection Rationale** | High vulnerability to rapid inundation from Pasig-Marikina River Basin | Historical flood data |
| **Road Network Source** | OpenStreetMap via OSMnx | `marikina_graph.graphml` |
| **Nodes (Intersections)** | 16,877 | Graph extraction |
| **Edges (Road Segments)** | 35,932 | Graph extraction |
| **Total Road Length** | 1,007.18 km | Computed from graph |
| **Coordinate System** | WGS84 (EPSG:4326) | Standard geographic |

### 2.2 Flood Hazard Data

| Parameter | Specification |
|-----------|---------------|
| **Data Format** | GeoTIFF raster maps |
| **Scenarios** | 72 maps (4 return periods × 18 time steps) |
| **Return Periods** | 2-year, 5-year, 10-year, 25-year |
| **Resolution** | 372 × 368 pixels |
| **Depth Categories** | Safe (<15cm), Passable (15-30cm), Dangerous (30-45cm), Impassable (>45cm) |

### 2.3 System Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           MAS-FRO Architecture                               │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐    ┌─────────────┐  │
│  │ ScoutAgent  │    │ FloodAgent  │    │ HazardAgent │    │RoutingAgent │  │
│  │ (NLP/ML)    │───▶│ (Official)  │───▶│ (Fusion)    │───▶│ (A*)        │  │
│  └─────────────┘    └─────────────┘    └─────────────┘    └─────────────┘  │
│         │                  │                  │                  │          │
│         └──────────────────┴──────────────────┴──────────────────┘          │
│                              │                                              │
│                    ┌─────────▼─────────┐                                    │
│                    │   MessageQueue    │                                    │
│                    │   (ACL Protocol)  │                                    │
│                    └─────────┬─────────┘                                    │
│                              │                                              │
│         ┌────────────────────┼────────────────────┐                         │
│         │                    │                    │                         │
│  ┌──────▼──────┐    ┌───────▼───────┐    ┌──────▼──────┐                   │
│  │ Graph       │    │ WebSocket     │    │ Performance │                   │
│  │ Environment │    │ Manager       │    │ Monitor     │                   │
│  └─────────────┘    └───────────────┘    └─────────────┘                   │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

#### 2.3.1 Backend Components

| Component | Technology | Purpose |
|-----------|------------|---------|
| **Framework** | FastAPI (Python 3.10+) | RESTful API + WebSocket |
| **Graph Library** | NetworkX MultiDiGraph | Road network representation |
| **Spatial Library** | OSMnx | Map data extraction & spatial indexing |
| **ML Framework** | scikit-learn, spaCy | NLP and classification models |
| **State Management** | DynamicGraphEnvironment | Shared agent state |
| **Communication** | FIPA-ACL Protocol | Inter-agent messaging |

#### 2.3.2 Frontend Components

| Component | Technology | Purpose |
|-----------|------------|---------|
| **Framework** | Next.js 15 | React-based web application |
| **Mapping** | Leaflet, React-Leaflet, Mapbox GL | Interactive map visualization |
| **Real-time** | WebSocket Client | Live flood updates |

---

## 3. Experimental Variables

### 3.1 Independent Variables (Factors)

#### Factor 1: Flood Scenario Intensity

| Level | Description | Depth Range | Risk Characteristics |
|-------|-------------|-------------|----------------------|
| **Light** | Minimal flooding | 0-15 cm | Low risk, all roads passable |
| **Medium** | Moderate flooding | 15-45 cm | Dangerous for small vehicles |
| **Heavy** | Severe flooding | >45 cm | Impassable for most vehicles |

#### Factor 2: Routing Algorithm Mode

| Mode | Risk Penalty (λ) | Description | Behavioral Interpretation |
|------|------------------|-------------|---------------------------|
| **SAFEST** | 100,000 | Maximum risk avoidance | Prefers 100km detour over maximum risk edge |
| **BALANCED** | 2,000 | Moderate safety/speed trade-off | Prefers 2km detour over maximum risk edge |
| **FASTEST** | 0 | Pure distance optimization | Blocks only impassable roads (risk ≥ 0.9) |
| **Baseline** | N/A | Standard Dijkstra/A* | No risk awareness |

**Virtual Meters Justification**: The risk penalty λ converts risk scores (0-1 scale) to distance units (meters) to prevent heuristic domination in A* algorithm. Edge cost formula:

```
cost = distance_meters + (λ × risk_score)
```

#### Factor 3: Risk Decay Function

| Function | Formula | Decay Characteristics |
|----------|---------|----------------------|
| **Linear** | `1 - (d / radius)` | Uniform decay |
| **Exponential** | `e^(-d / radius)` | Rapid initial decay |
| **Gaussian** | `e^(-(d² / (2 × (radius/2)²)))` | Smooth decay (default) |

Where `d` = distance from hazard center, `radius` = 800m (configurable)

#### Factor 4: Data Source Configuration

| Configuration | Components | Use Case |
|---------------|------------|----------|
| **Official Only** | FloodAgent (PAGASA, OpenWeatherMap) | Baseline official data |
| **Crowdsourced Only** | ScoutAgent (social media) | Citizen science validation |
| **Fusion** | HazardAgent (both sources) | Full system operation |

### 3.2 Dependent Variables (Metrics)

#### 3.2.1 Routing Performance Metrics

| Metric | Definition | Unit | Target |
|--------|------------|------|--------|
| **Computation Time** | A* algorithm execution time | milliseconds | < 100ms |
| **Route Success Rate** | Valid routes found / total requests | percentage | > 95% |
| **Risk Reduction** | (Baseline risk - Route risk) / Baseline risk × 100 | percentage | > 30% |
| **Distance Overhead** | (Route distance - Shortest path) / Shortest path × 100 | percentage | < 50% |
| **Max Edge Risk** | Maximum risk score along route | 0-1 scale | < 0.7 |
| **Cumulative Path Risk** | Sum of (edge_risk × edge_length) for all edges | risk-meters | Minimize |

#### 3.2.2 System Latency Metrics

| Metric | Definition | Unit | Target |
|--------|------------|------|--------|
| **WebSocket Message Latency** | Time from send to receive | milliseconds | < 50ms |
| **Risk Update Propagation** | Backend calculation to frontend render | milliseconds | < 200ms |
| **Graph Update Time** | Time to update all affected edges | milliseconds | < 500ms |
| **Cache Hit Rate** | Cache hits / total lookups × 100 | percentage | > 70% |

#### 3.2.3 Risk Assessment Metrics

| Metric | Definition | Unit |
|--------|------------|------|
| **Depth-to-Risk Accuracy** | RMSE between predicted and FEMA-standard risk | 0-1 scale |
| **Spatial Propagation Accuracy** | IoU between predicted and actual flood extent | percentage |
| **Risk Decay Calibration** | Correlation between decay model and observed risk | Pearson r |

#### 3.2.4 NLP Pipeline Metrics

| Metric | Definition | Target |
|--------|------------|--------|
| **Flood Classification Accuracy** | Correct flood/non-flood classification | > 85% |
| **Severity Classification Accuracy** | Correct severity level (critical/dangerous/minor/none) | > 75% |
| **Location Extraction Accuracy (NER)** | Correct location entity extraction | > 80% |
| **Geocoding Success Rate** | Successfully mapped locations to coordinates | > 70% |

---

## 4. Experimental Procedures

### 4.1 Experiment 1: Routing Algorithm Evaluation

#### 4.1.1 Objective
Compare the Risk-Aware A* algorithm against baseline pathfinding under varying flood conditions.

#### 4.1.2 Methodology

**Sample Generation**:
- Generate 1,000 randomized origin-destination (O-D) pairs across Marikina road network
- Ensure geographic distribution covers all 21 barangays
- Exclude O-D pairs with same start/end node

**Test Conditions**:

| Condition ID | Flood Scenario | Algorithm Mode | Risk Penalty (λ) |
|--------------|----------------|----------------|------------------|
| C1 | Light | Baseline | N/A |
| C2 | Light | FASTEST | 0 |
| C3 | Light | BALANCED | 2,000 |
| C4 | Light | SAFEST | 100,000 |
| C5 | Medium | Baseline | N/A |
| C6 | Medium | FASTEST | 0 |
| C7 | Medium | BALANCED | 2,000 |
| C8 | Medium | SAFEST | 100,000 |
| C9 | Heavy | Baseline | N/A |
| C10 | Heavy | FASTEST | 0 |
| C11 | Heavy | BALANCED | 2,000 |
| C12 | Heavy | SAFEST | 100,000 |

**Procedure**:
1. Load flood scenario into DynamicGraphEnvironment
2. Initialize HazardAgent with risk calculations
3. For each O-D pair:
   a. Record start timestamp
   b. Execute routing algorithm
   c. Record end timestamp
   d. Extract: path, distance, risk scores, warnings
4. Repeat for all algorithm modes
5. Store results in structured format

**Data Collection Schema**:

```python
{
    "condition_id": str,
    "od_pair_id": int,
    "origin": {"lat": float, "lon": float},
    "destination": {"lat": float, "lon": float},
    "algorithm": str,
    "risk_penalty": float,
    "flood_scenario": str,
    "computation_time_ms": float,
    "route_found": bool,
    "path_distance_m": float,
    "path_risk_cumulative": float,
    "path_risk_max": float,
    "path_risk_avg": float,
    "num_segments": int,
    "warnings": list[dict],
    "timestamp": datetime
}
```

#### 4.1.3 Analysis Plan

| Analysis | Method | Purpose |
|----------|--------|---------|
| **Computation Time** | ANOVA with post-hoc Tukey HSD | Compare algorithm performance |
| **Risk Reduction** | Paired t-test vs baseline | Quantify safety improvement |
| **Distance Overhead** | Regression analysis | Trade-off characterization |
| **Route Success** | Chi-square test | Compare success rates |

### 4.2 Experiment 2: Real-Time System Latency Test

#### 4.2.1 Objective
Measure end-to-end latency for flood data propagation from collection to visualization.

#### 4.2.2 Methodology

**Test Setup**:
- Deploy full system stack (backend + frontend)
- Configure WebSocket connection with automatic reconnection
- Enable performance monitoring via PerformanceMonitor singleton

**Latency Measurement Points**:

```
┌─────────────┐    T1    ┌─────────────┐    T2    ┌─────────────┐    T3    ┌─────────────┐
│ Data Source │ ──────▶ │ FloodAgent  │ ──────▶ │ HazardAgent │ ──────▶ │ WebSocket   │
│ (PAGASA/API)│         │ Processing  │         │ Risk Calc   │         │ Broadcast   │
└─────────────┘         └─────────────┘         └─────────────┘         └─────────────┘
                                                                               │
                                                                               │ T4
                                                                               ▼
                                                                        ┌─────────────┐
                                                                        │ Frontend    │
                                                                        │ Render      │
                                                                        └─────────────┘
```

| Interval | Description | Target |
|----------|-------------|--------|
| T1 | Data source fetch | < 2000ms |
| T2 | Agent processing + ACL messaging | < 100ms |
| T3 | Risk calculation + graph update | < 500ms |
| T4 | WebSocket transmission + render | < 200ms |
| **Total** | End-to-end latency | < 3000ms |

**Test Conditions**:

| Load Level | Concurrent Users | Update Frequency |
|------------|------------------|------------------|
| Low | 10 | 5 minutes |
| Medium | 50 | 2 minutes |
| High | 100 | 1 minute |
| Stress | 200 | 30 seconds |

**Procedure**:
1. Deploy system with performance monitoring enabled
2. Simulate concurrent WebSocket connections
3. Trigger flood data updates at specified intervals
4. Record timestamps at each measurement point
5. Calculate interval durations and total latency
6. Repeat for 100 update cycles per load level

**Data Collection Schema**:

```python
{
    "test_id": str,
    "load_level": str,
    "update_cycle": int,
    "t1_data_fetch_ms": float,
    "t2_agent_processing_ms": float,
    "t3_risk_calculation_ms": float,
    "t4_websocket_render_ms": float,
    "total_latency_ms": float,
    "cache_hit_rate": float,
    "memory_usage_mb": float,
    "timestamp": datetime
}
```

#### 4.2.3 Analysis Plan

| Analysis | Method | Purpose |
|----------|--------|---------|
| **Latency Distribution** | Descriptive statistics (mean, median, P95, P99) | Characterize performance |
| **Load Impact** | Linear regression | Quantify scalability |
| **Bottleneck Identification** | Pareto analysis | Optimize critical paths |

### 4.3 Experiment 3: NLP Pipeline Validation

#### 4.3.1 Objective
Evaluate the ScoutAgent's ML pipeline for processing crowdsourced flood reports.

#### 4.3.2 Methodology

**Dataset Preparation**:

| Dataset | Size | Purpose | Source |
|---------|------|---------|--------|
| **Training Set** | 8,000 posts | Model training | Historical Twitter data |
| **Validation Set** | 1,000 posts | Hyperparameter tuning | Hold-out split |
| **Test Set** | 1,000 posts | Final evaluation | Synthetic + real data |

**Language Distribution** (Test Set):
- Filipino: 40%
- English: 35%
- Taglish (mixed): 25%

**Component Evaluation**:

| Component | Model | Evaluation Metric |
|-----------|-------|-------------------|
| **Flood Classifier** | Logistic Regression | Accuracy, Precision, Recall, F1 |
| **Severity Classifier** | Random Forest | Macro-F1, Confusion Matrix |
| **Location Extractor (NER)** | spaCy Custom Model | Entity-level F1 |
| **Geocoder** | Fuzzy Matching (difflib) | Success Rate, Distance Error |

**Severity Labels**:

| Label | Severity Score | Description |
|-------|---------------|-------------|
| none | 0.0 | No flooding reported |
| minor | 0.3 | Ankle/gutter level, passable |
| dangerous | 0.65 | Knee/waist level, impassable |
| critical | 0.95 | Chest/neck level, life-threatening |

**Procedure**:
1. Load NLPProcessor with trained models
2. For each test post:
   a. Run flood classification
   b. If flood-related, run severity classification
   c. Extract location entities
   d. Attempt geocoding
   e. Compare against ground truth labels
3. Compute evaluation metrics
4. Analyze error patterns

**Data Collection Schema**:

```python
{
    "post_id": str,
    "text": str,
    "language": str,
    "ground_truth": {
        "is_flood_related": bool,
        "severity": str,
        "location": str,
        "coordinates": {"lat": float, "lon": float}
    },
    "prediction": {
        "is_flood_related": bool,
        "flood_confidence": float,
        "severity": str,
        "severity_confidence": float,
        "location": str,
        "location_confidence": float,
        "coordinates": {"lat": float, "lon": float}
    },
    "evaluation": {
        "flood_correct": bool,
        "severity_correct": bool,
        "location_correct": bool,
        "geocoding_success": bool,
        "coordinate_error_m": float
    }
}
```

#### 4.3.3 Analysis Plan

| Analysis | Method | Purpose |
|----------|--------|---------|
| **Classification Performance** | Confusion matrix, ROC-AUC | Model accuracy assessment |
| **Error Analysis** | Manual review of misclassifications | Identify failure modes |
| **Language Impact** | Stratified analysis by language | Bilingual performance |

### 4.4 Experiment 4: Risk Assessment Calibration

#### 4.4.1 Objective
Validate the FEMA-calibrated sigmoid depth-to-risk model against hydrological standards.

#### 4.4.2 Methodology

**FEMA Sigmoid Model**:

```python
risk = 1 / (1 + exp(-k × (depth - x0)))
```

Where:
- `k = 8.0` (steepness parameter)
- `x0 = 0.3m` (inflection point - 50% risk at 0.3m depth)

**Validation Points** (FEMA Standards):

| Depth (m) | Expected Risk | Interpretation |
|-----------|---------------|----------------|
| 0.0 | 0.08 | Dry conditions |
| 0.15 | 0.23 | Ankle level - Safe for pedestrians |
| 0.30 | 0.50 | FEMA threshold - 50% risk |
| 0.45 | 0.77 | Knee level - Dangerous |
| 0.60 | 0.92 | Waist level - Critical |

**Hydrological Energy Head Model** (Kreibich et al., 2009):

```python
E = depth + (velocity² / (2 × g))
```

Where `g = 9.81 m/s²`

**Risk Category Thresholds**:

| Energy Head (m) | Risk Level | System Risk Score |
|-----------------|------------|-------------------|
| < 0.3 | Low | 0.0 - 0.4 |
| 0.3 - 0.6 | Moderate | 0.4 - 0.7 |
| > 0.6 | High | 0.7 - 1.0 |

**Procedure**:
1. Generate synthetic flood scenarios with known depths
2. Calculate risk using system sigmoid model
3. Compare against FEMA reference values
4. Calculate RMSE and correlation
5. Validate spatial decay (Gaussian) against field observations

#### 4.4.3 Analysis Plan

| Analysis | Method | Purpose |
|----------|--------|---------|
| **Model Fit** | RMSE, R² | Quantify accuracy |
| **Threshold Calibration** | Sensitivity analysis | Optimize k and x0 |
| **Spatial Validation** | IoU with flood extent maps | Verify propagation |

### 4.5 Experiment 5: Multi-Agent Coordination Test

#### 4.5.1 Objective
Evaluate the effectiveness of inter-agent communication via ACL protocol.

#### 4.5.2 Methodology

**Message Flow Analysis**:

```
ScoutAgent ──[INFORM: scout_data]──▶ HazardAgent
FloodAgent ──[INFORM: flood_data]──▶ HazardAgent
HazardAgent ──[INFORM: risk_update]──▶ RoutingAgent
EvacuationManager ──[REQUEST: route]──▶ RoutingAgent
RoutingAgent ──[INFORM: route_result]──▶ EvacuationManager
```

**Metrics**:

| Metric | Definition | Target |
|--------|------------|--------|
| **Message Delivery Rate** | Successfully delivered / total sent | > 99.9% |
| **Message Latency** | Time from send to receive | < 10ms |
| **Queue Depth** | Average messages waiting | < 100 |
| **Dead Letter Rate** | Failed messages / total sent | < 0.1% |

**Test Scenarios**:

| Scenario | Description | Load |
|----------|-------------|------|
| Normal | Standard operation | 10 msg/sec |
| Burst | Sudden flood alert | 100 msg/sec |
| Sustained | Continuous updates | 50 msg/sec for 1 hour |

---

## 5. Data Analysis Framework

### 5.1 Statistical Methods

| Test | Application | Assumptions |
|------|-------------|-------------|
| **ANOVA** | Compare algorithm modes | Normal distribution, homogeneity |
| **Tukey HSD** | Pairwise comparisons | Following significant ANOVA |
| **Paired t-test** | Before/after comparisons | Paired observations |
| **Chi-square** | Categorical comparisons | Expected counts > 5 |
| **Mann-Whitney U** | Non-parametric comparison | Non-normal data |
| **Linear Regression** | Relationship modeling | Linearity, independence |

### 5.2 Performance Thresholds

| Metric | Acceptable | Good | Excellent |
|--------|------------|------|-----------|
| **Computation Time** | < 500ms | < 200ms | < 100ms |
| **Route Success Rate** | > 90% | > 95% | > 99% |
| **Risk Reduction** | > 20% | > 30% | > 50% |
| **Distance Overhead** | < 100% | < 50% | < 25% |
| **System Latency** | < 5000ms | < 2000ms | < 1000ms |
| **NLP Accuracy** | > 70% | > 80% | > 90% |

### 5.3 Visualization Plan

| Visualization | Purpose | Variables |
|---------------|---------|-----------|
| **Box plots** | Distribution comparison | Computation time by algorithm |
| **Line charts** | Trend analysis | Latency over time |
| **Heat maps** | Spatial analysis | Risk distribution on map |
| **Confusion matrices** | Classification analysis | NLP model performance |
| **Pareto charts** | Bottleneck identification | Latency components |
| **Scatter plots** | Trade-off analysis | Risk vs. distance |

---

## 6. Experimental Timeline

| Phase | Duration | Activities |
|-------|----------|------------|
| **Setup** | Week 1 | Environment configuration, data preparation |
| **Pilot** | Week 2 | Small-scale tests, protocol refinement |
| **Experiment 1** | Week 3-4 | Routing algorithm evaluation |
| **Experiment 2** | Week 5 | System latency testing |
| **Experiment 3** | Week 6 | NLP pipeline validation |
| **Experiment 4** | Week 7 | Risk assessment calibration |
| **Experiment 5** | Week 8 | Multi-agent coordination |
| **Analysis** | Week 9-10 | Data analysis and reporting |

---

## 7. Expected Outcomes

### 7.1 Hypothesis Statements

| ID | Hypothesis | Metric | Expected Result |
|----|------------|--------|-----------------|
| H1 | Risk-Aware A* reduces path risk compared to baseline | Risk Reduction | > 30% |
| H2 | BALANCED mode provides optimal safety-efficiency trade-off | Distance Overhead | < 50% with > 30% risk reduction |
| H3 | System latency meets real-time requirements | Total Latency | < 3000ms |
| H4 | NLP pipeline accurately classifies flood reports | Accuracy | > 85% |
| H5 | FEMA sigmoid model accurately predicts risk | RMSE | < 0.1 |

### 7.2 Deliverables

1. **Performance Benchmark Report**: Quantitative analysis of algorithm performance
2. **System Latency Profile**: End-to-end timing analysis
3. **NLP Evaluation Report**: Classification and extraction accuracy
4. **Risk Model Calibration Report**: Validation against FEMA standards
5. **Recommendations Document**: System optimization suggestions

---

## 8. Limitations and Threats to Validity

### 8.1 Internal Validity

| Threat | Mitigation |
|--------|------------|
| **Selection bias** | Random O-D pair generation |
| **Instrumentation** | Consistent measurement protocols |
| **Testing effects** | Separate training/test datasets |

### 8.2 External Validity

| Threat | Mitigation |
|--------|------------|
| **Geographic specificity** | Document Marikina-specific assumptions |
| **Temporal validity** | Use multiple flood scenarios |
| **Technology changes** | Document software versions |

### 8.3 Known Limitations

1. **Simulation Mode**: ScoutAgent operates in simulation-only mode (no live Twitter API)
2. **Network Variability**: Real-world WebSocket performance may vary
3. **Model Training Data**: Limited Filipino language training corpus
4. **Flood Model Resolution**: GeoTIFF resolution may miss micro-scale features

---

## 9. Ethical Considerations

1. **Data Privacy**: No personally identifiable information collected
2. **Safety**: System recommendations should supplement, not replace, official evacuation guidance
3. **Accessibility**: Results should be shared with local disaster management authorities
4. **Transparency**: Document all model limitations and failure modes

---

## 10. Appendices

### Appendix A: System Configuration Parameters

```python
# Routing Configuration
SAFEST_RISK_PENALTY = 100_000      # Virtual meters per risk unit
BALANCED_RISK_PENALTY = 2_000      # Virtual meters per risk unit
FASTEST_RISK_PENALTY = 0           # No risk penalty
IMPASSABILITY_THRESHOLD = 0.9      # Risk score blocking threshold

# Hazard Configuration
RISK_RADIUS = 800                  # meters
DECAY_FUNCTION = "gaussian"        # linear, exponential, gaussian
SIGMOID_K = 8.0                    # Steepness parameter
SIGMOID_X0 = 0.3                   # Inflection point (meters)
RISK_FLOOR = 0.15                  # Minimum residual risk

# Risk Weights
FLOOD_DEPTH_WEIGHT = 0.50          # 50%
CROWDSOURCED_WEIGHT = 0.30         # 30%
HISTORICAL_WEIGHT = 0.20           # 20%

# TTL Settings
SCOUT_TTL_MINUTES = 45             # Scout report validity
FLOOD_TTL_MINUTES = 90             # Flood data validity
CACHE_TTL_SECONDS = 3600           # Node cache lifetime

# NLP Settings
FLOOD_CONFIDENCE_THRESHOLD = 0.5   # Classification threshold
FUZZY_MATCH_THRESHOLD = 0.6        # Location matching threshold
```

### Appendix B: Sample Test Data Format

```json
{
  "od_pairs": [
    {
      "id": 1,
      "origin": {"lat": 14.6507, "lon": 121.1029, "barangay": "Concepcion Uno"},
      "destination": {"lat": 14.6234, "lon": 121.0856, "barangay": "Marikina Heights"}
    }
  ],
  "flood_scenarios": [
    {
      "id": "light_1",
      "intensity": "light",
      "return_period": "2-year",
      "time_step": 6,
      "geotiff_path": "data/flood_maps/2yr_t6.tif"
    }
  ],
  "test_posts": [
    {
      "id": 1,
      "text": "Baha na sa Tumana, lampas tuhod na ang tubig! #MarikinaPH",
      "language": "filipino",
      "ground_truth": {
        "is_flood_related": true,
        "severity": "dangerous",
        "location": "Tumana"
      }
    }
  ]
}
```

### Appendix C: Evaluation Metrics Formulas

**Risk Reduction**:
```
Risk_Reduction = (Baseline_Risk - Route_Risk) / Baseline_Risk × 100%
```

**Distance Overhead**:
```
Distance_Overhead = (Route_Distance - Shortest_Distance) / Shortest_Distance × 100%
```

**Cumulative Path Risk**:
```
CPR = Σ (edge_risk_i × edge_length_i) for all edges in path
```

**F1 Score**:
```
F1 = 2 × (Precision × Recall) / (Precision + Recall)
```

**RMSE (Root Mean Square Error)**:
```
RMSE = √(Σ(predicted_i - actual_i)² / n)
```

---

## References

1. Hart, P. E., Nilsson, N. J., & Raphael, B. (1968). A Formal Basis for the Heuristic Determination of Minimum Cost Paths. *IEEE Transactions on Systems Science and Cybernetics*, 4(2), 100-107.

2. Kreibich, H., Piroth, K., Seifert, I., Maiwald, H., Kunert, U., Schwarz, J., ... & Thieken, A. H. (2009). Is flow velocity a significant parameter in flood damage modelling? *Natural Hazards and Earth System Sciences*, 9(5), 1679-1692.

3. FEMA. (2020). *Guidance for Flood Risk Analysis and Mapping: Flood Depth and Analysis Grids*. Federal Emergency Management Agency.

4. Boeing, G. (2017). OSMnx: New Methods for Acquiring, Constructing, Analyzing, and Visualizing Complex Street Networks. *Computers, Environment and Urban Systems*, 65, 126-139.

5. Foundation for Intelligent Physical Agents (FIPA). (2002). *FIPA ACL Message Structure Specification*. IEEE Computer Society.

---

*Document Version: 1.0*
*Last Updated: January 2026*
*System Version: MAS-FRO Backend v1.0*
