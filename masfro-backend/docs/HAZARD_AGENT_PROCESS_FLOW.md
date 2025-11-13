# HazardAgent Process Flow Documentation

## Overview
The HazardAgent serves as the central data fusion and risk assessment hub in the MAS-FRO system, processing flood data from multiple sources and updating the Dynamic Graph Environment with calculated risk scores.

## Complete Process Flow Diagram

```mermaid
graph TB
    Start([HazardAgent Initialization])
    
    %% Initialization
    Start --> Init{Initialize Components}
    Init --> Cache[Setup Data Caches<br/>flood_data_cache<br/>scout_data_cache]
    Init --> Weights[Configure Risk Weights<br/>flood: 0.5<br/>crowdsourced: 0.3<br/>historical: 0.2]
    Init --> GeoTIFF{GeoTIFF Enabled?}
    GeoTIFF -->|Yes| InitGeo[Initialize GeoTIFFService]
    GeoTIFF -->|No| SkipGeo[Skip GeoTIFF]
    InitGeo --> SetScenario[Set Default Scenario<br/>rr01, time_step=1]
    SkipGeo --> SetScenario
    
    %% Data Ingestion
    SetScenario --> Ready([Agent Ready])
    Ready --> DataIn{Data Input}
    
    DataIn --> FloodPath[FloodAgent Data]
    DataIn --> ScoutPath[ScoutAgent Data]
    DataIn --> StepTrigger[Periodic Step]
    
    %% FloodAgent Path
    FloodPath --> ValidateFlood{Validate<br/>Flood Data}
    ValidateFlood -->|Valid| CacheFlood[Cache Flood Data<br/>by Location]
    ValidateFlood -->|Invalid| LogWarning1[Log Warning]
    CacheFlood --> TriggerProcess[Trigger<br/>process_and_update()]
    
    %% ScoutAgent Path
    ScoutPath --> ValidateScout{Validate<br/>Scout Reports}
    ValidateScout -->|Valid| CacheScout[Append to<br/>Scout Cache]
    ValidateScout -->|Invalid| LogWarning2[Log Warning]
    
    %% Step Trigger Path
    StepTrigger --> CheckCache{Cache<br/>Has Data?}
    CheckCache -->|Yes| TriggerProcess
    CheckCache -->|No| Ready
    
    %% Main Processing Flow
    TriggerProcess --> ProcessUpdate[process_and_update()]
    ProcessUpdate --> FuseData[fuse_data()]
    
    %% Data Fusion Detail
    FuseData --> ProcessFloodCache[Process Flood Cache]
    ProcessFloodCache --> CalcDepthRisk[Calculate Depth Risk<br/>depth/2.0, max 1.0]
    CalcDepthRisk --> ApplyFloodWeight[Apply Weight: 0.5]
    
    FuseData --> ProcessScoutCache[Process Scout Cache]
    ProcessScoutCache --> CalcSeverity[severity × confidence]
    CalcSeverity --> ApplyScoutWeight[Apply Weight: 0.3]
    
    ApplyFloodWeight --> Normalize[Normalize to 0-1 Scale]
    ApplyScoutWeight --> Normalize
    
    %% Risk Calculation
    Normalize --> CalcRisk[calculate_risk_scores()]
    CalcRisk --> QueryGeoTIFF{GeoTIFF<br/>Enabled?}
    
    QueryGeoTIFF -->|Yes| GetEdgeDepths[get_edge_flood_depths()]
    QueryGeoTIFF -->|No| SkipDepths[Use Fused Data Only]
    
    GetEdgeDepths --> ForEachEdge[For Each Edge]
    ForEachEdge --> QueryEndpoints[Query Both Endpoints]
    QueryEndpoints --> AvgDepth[Average Depths]
    AvgDepth --> ConvertRisk[Convert Depth to Risk]
    
    ConvertRisk --> RiskMapping{Depth Range}
    RiskMapping -->|0-0.3m| Low[Risk: 0-0.3]
    RiskMapping -->|0.3-0.6m| Moderate[Risk: 0.3-0.6]
    RiskMapping -->|0.6-1.0m| High[Risk: 0.6-0.8]
    RiskMapping -->|>1.0m| Critical[Risk: 0.8-1.0]
    
    Low --> CombineRisk[Combine Risks]
    Moderate --> CombineRisk
    High --> CombineRisk
    Critical --> CombineRisk
    SkipDepths --> CombineRisk
    
    CombineRisk --> ApplyEnv[Apply Environmental<br/>Factors]
    
    %% Environment Update
    ApplyEnv --> UpdateEnv[update_environment()]
    UpdateEnv --> ForEachRisk[For Each Edge Risk]
    ForEachRisk --> UpdateEdge[update_edge_risk()]
    UpdateEdge --> Success{Update<br/>Success?}
    Success -->|Yes| NextEdge[Next Edge]
    Success -->|No| LogError[Log Error]
    LogError --> NextEdge
    NextEdge --> Complete{All Edges<br/>Done?}
    Complete -->|No| ForEachRisk
    Complete -->|Yes| LogComplete[Log Completion Stats]
    
    LogComplete --> Ready
```

## Detailed Process Steps

### 1. Initialization Phase
- **Data Caches Setup**: Initialize `flood_data_cache` (dict) and `scout_data_cache` (list)
- **Risk Weight Configuration**: Set weights for data fusion (flood: 50%, crowdsourced: 30%, historical: 20%)
- **GeoTIFF Service**: Conditionally initialize based on `enable_geotiff` flag
- **Default Scenario**: Set to rr01 (2-year return period), time_step 1 (1 hour)

### 2. Data Ingestion Pipeline

#### FloodAgent Data Path
```python
process_flood_data() → validate → cache → trigger process_and_update()
```
- Validates required fields: location, flood_depth, timestamp
- Validates flood depth range: 0-10 meters
- Caches by location key
- Immediately triggers processing

#### ScoutAgent Data Path
```python
process_scout_data() → validate each → append to cache
```
- Validates required fields: location, severity, timestamp
- Validates severity range: 0-1 scale
- Validates confidence range: 0-1 scale
- Accumulates reports in list

### 3. Data Fusion Process
Combines multiple data sources with weighted averaging:

1. **Official Flood Data Processing**:
   - Convert flood depth to risk (depth/2.0, capped at 1.0)
   - Apply flood weight (0.5)
   - Set high confidence (0.8)

2. **Crowdsourced Data Processing**:
   - Calculate weighted severity (severity × confidence)
   - Apply crowdsourced weight (0.3)
   - Set variable confidence (confidence × 0.6)

3. **Normalization**: Cap all values at 1.0

### 4. Risk Score Calculation

#### GeoTIFF Integration (if enabled)
1. Query flood depths for all edges
2. For each edge, query both endpoints
3. Average the depths
4. Convert to risk score:

| Depth Range | Risk Range | Calculation |
|------------|------------|-------------|
| 0-0.3m | 0-0.3 | Linear mapping |
| 0.3-0.6m | 0.3-0.6 | Linear scaling |
| 0.6-1.0m | 0.6-0.8 | Compressed scaling |
| >1.0m | 0.8-1.0 | Capped scaling |

#### Environmental Factor Application
- Applies system-wide conditions to all edges
- Uses maximum of current risk and combined risk
- Caps final risk at 1.0

### 5. Graph Environment Update
```python
For each edge with risk score:
    environment.update_edge_risk(u, v, key, risk)
```
- Updates edge attributes in NetworkX graph
- Handles failures gracefully with error logging
- Reports statistics on completion

## Data Flow Summary

```
Input Sources           Processing              Output
─────────────          ────────────           ────────
FloodAgent  ──┐                               
              ├──> Data Fusion ──> Risk       Graph
ScoutAgent  ──┤                    Scores ──> Environment
              │                                Updates
GeoTIFF     ──┘
```

## Timezone Configuration
All timestamps now use Philippine Time (UTC+8) via the `timezone_utils` module:
- `get_philippine_time()` for current timestamps
- Timezone-aware datetime objects throughout
- Consistent timestamp handling across all agents

## Key Features
1. **Multi-source Data Fusion**: Combines official, crowdsourced, and GeoTIFF data
2. **Configurable Risk Weights**: Adjustable weighting for different data sources
3. **Dynamic Scenario Selection**: Runtime configuration of flood scenarios
4. **Graceful Degradation**: Continues operation if GeoTIFF unavailable
5. **Real-time Processing**: Immediate processing on flood data receipt
6. **Cache Management**: Age-based cache cleanup for data freshness

## Performance Considerations
- Edge flood depth queries: O(E) where E = number of edges
- Data fusion: O(L + R) where L = locations, R = reports
- Risk calculation: O(E) for all edges
- Environment update: O(E) for affected edges

## Error Handling
- Input validation with detailed logging
- Graceful handling of missing GeoTIFF service
- Individual edge update failure isolation
- Cache cleanup for stale data (>1 hour by default)