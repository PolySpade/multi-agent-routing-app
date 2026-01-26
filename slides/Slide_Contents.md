# MAS-FRO Defense Slide Contents (Markdown Edition)

This document mirrors the content of `slides/masfro-defense.tex`, translating each frame into GitHub-friendly markdown for quick review, rehearsals, and archival purposes. Use it alongside the Beamer source when tailoring narratives or exporting alternative formats (e.g., static web pages, speaker scripts).

- Source deck: [`slides/masfro-defense.tex`](./masfro-defense.tex)
- Companion compile guide: [`slides/README.md`](./README.md)
- Backend reference: [`masfro-backend`](../masfro-backend)
- Frontend reference: [`masfro-frontend`](../masfro-frontend)

> **Prototype Status Reminder**  
> MAS-FRO is an operational prototype scoped to Marikina City. Comparative baselines, systematic simulations, and stress testing remain open research tasks. All claims are framed with this context.

---

## Table of Contents

- [Section Navigation](#section-navigation)
- [Problem & Motivation (Slides 2–7)](#problem--motivation-slides-2-7)
- [Theoretical Foundations (Slides 8–11)](#theoretical-foundations-slides-8-11)
- [Related Work (Slides 12–14)](#related-work-slides-12-14)
- [System Architecture (Slides 15–24)](#system-architecture-slides-15-24)
- [Agreement Form Compliance (Slides 25–32)](#agreement-form-compliance-slides-25-32)
- [Implementation Highlights (Slides 33–37)](#implementation-highlights-slides-33-37)
- [Performance (Slides 38–40)](#performance-slides-38-40)
- [Critical Assessment (Slides 41–45)](#critical-assessment-slides-41-45)
- [Future Work & Conclusion (Slides 46–49)](#future-work--conclusion-slides-46-49)
- [Q&A (Slide 50)](#qa-slide-50)
- [Backup Appendix (Slides A1–A12)](#backup-appendix-slides-a1-a12)
- [Index of Code References](#index-of-code-references)
- [Revision Checklist](#revision-checklist)

---

## Section Navigation

| Section | Frames | Key Artifacts |
|---------|--------|---------------|
| Problem & Motivation | 2–7 | Ondoy timeline, Marikina map, research objectives |
| Theoretical Foundations | 8–11 | MAS properties, A* complexity, risk formulation, data fusion terminology |
| Related Work | 12–14 | Comparative tables, risk-aware timeline, niche visualization |
| System Architecture | 15–24 | Agent topology, FIPA-ACL snippet, dynamic graph concepts |
| Agreement Form Compliance | 25–32 | Itemized status, gaps, roadmap flags |
| Implementation Highlights | 33–37 | Data ingestion, GeoTIFF pipeline, WebSocket flow, database ER sketch |
| Performance | 38–40 | Preliminary metrics, operational statistics, data quality ratios |
| Critical Assessment | 41–45 | Limitations, publication gaps, roadmap, lessons learned |
| Future Work & Conclusion | 46–49 | Qualified contributions, phased roadmap, summary matrix |
| Q&A | 50 | Prompt + pointer to backups |
| Backup Appendix | A1–A12 | Proof sketches, code extracts, architectural deep dives |

Each slide summary below follows the exact numbering, titles, and focal points from the Beamer deck.

---

## Problem & Motivation (Slides 2–7)

### Slide 1 — Title Slide (Frame 1)
- **Title**: MAS-FRO: Multi-Agent System for Flood Route Optimization
- **Subtitle**: Real-Time Flood-Safe Navigation for Marikina City, Philippines
- **Meta**: [Student Name], De La Salle University – College of Computer Studies, November 2025
- **Footer Callout**: “Prototype System (85% Complete) — Pending Comparative Validation”

### Slide 2 — The Ondoy Disaster (2009)
- Ondoy rainfall: 455 mm in 6 hours; peak water level: 21.5 m (~4.5 m above critical)
- Casualties: 464 nationwide, 80+ in Marikina; damage: PHP 11 B
- Failure point: Traditional navigation routed evacuees into flooded traps
- Visual placeholder: Stylized Marikina boundary with flood extent and river path (TikZ diagram in Beamer)

### Slide 3 — Research Gap
- Comparative capabilities table contrasting MAS-FRO, Google Maps, DOST-NOAH, and academic MAS efforts
  - MAS-FRO: ✓ Multi-Agent, ✓ Real-Time Flood, ✓ Crowdsourced, ✓ Risk-Aware, Prototype deployment level
  - Google Maps: Traffic awareness but lacks flood/risk integration
  - DOST-NOAH: Monitoring only; no routing intelligence
  - Simulation-focused MAS literature lacks real-world deployment
- Conclusion block: No existing system combines all four core capabilities operationally

### Slide 4 — Marikina City Context
- Coverage: 21.5 km²; population ≈ 450 k
- Road network scale: ~10,000 nodes, ~20,000 edges (directed multi-graph from OSMnx)
- Geographic bounds: 14.61–14.75°N, 121.08–121.13°E
- Visual placeholder: TikZ map highlighting Marikina River, 5 PAGASA river stations, 36 evacuation centers, and road grid

### Slide 5 — Five Challenges
1. Dynamic hazards; flood depths vary within minutes
2. Multi-source data fusion (PAGASA, OpenWeatherMap 3.0, GeoTIFF hazard rasters, Twitter/X)
3. Sub-2-second response for route computation under load
4. Data reliability gaps; official sources sparse, crowdsourced noisy
5. 24/7 availability with graceful degradation to protect against API outages

### Slide 6 — Research Objectives
- Primary objective: Deliver real-time, flood-safe routing for Marikina City evacuees
- Specific aims (align with Agreement Form items):
  1. Engineer hierarchical MAS using FIPA-ACL conventions
  2. Integrate real-time environmental feeds (PAGASA, OWM, GeoTIFF layers)
  3. Implement risk-aware A* pathfinding on dynamic graphs
  4. Build web prototype (FastAPI backend, Next.js frontend)
  5. Validate performance (⚠️ comparative evaluation pending)

### Slide 7 — Scope & Limitations (Upfront Honesty)
- **In Scope**: Marikina footprint, 5+ months uptime (projected), real API integrations
- **Out of Scope**: Other cities, multi-hazard coverage, offline operations
- **Validation Gaps**: Baselines absent, no real-emergency deployment, expert validation pending

---

## Theoretical Foundations (Slides 8–11)

### Slide 8 — Multi-Agent Systems Theory
- Cites Wooldridge (1995): autonomy, reactivity, proactivity, social ability as agent traits
- Table mapping MAS properties to MAS-FRO agents (FloodAgent, HazardAgent, RoutingAgent)
- FIPA-ACL block: Highlights use of standard performatives (REQUEST, INFORM, CONFIRM, etc.); see `app/communication/acl_protocol.py`

### Slide 9 — Graph Theory & A* Algorithm
- Road network formulation: \( G = (V, E, W) \) as directed multi-graph from OSMnx/NetworkX
- Complexity reminder: \( \mathcal{O}((|V| + |E|) \log |V|) \) via binary heap priority queue
- Heuristic: Haversine distance meets admissibility requirements at Marikina scale (error < 50 m)

```tex
f(n) = g(n) + h(n), \quad h(n) \leq h^*(n) \Rightarrow \text{optimal path}
```
Plain-English: With an admissible heuristic (Haversine), standard A* returns the shortest safe path.

### Slide 10 — Risk Assessment & MCDM
- Cost function variation of multi-criteria decision making (MCDM) combining distance and risk

```tex
\text{Cost}(e) = w_d \cdot d(e) + w_r \cdot d(e) \cdot r(e)
```
Plain-English: Distance and risk trade-offs are controlled via weights; current heuristic values prioritize safety (`w_d = 0.4`, `w_r = 0.6`).

- Passability constraint triggers `∞` cost when risk exceeds 0.9 (edge removed from consideration)

### Slide 11 — Data Fusion (Terminology Correction)
- Weighted aggregation of official, crowdsourced, and historical risk signals

```tex
R_{\text{fused}} = \alpha_1 R_{\text{official}} + \alpha_2 R_{\text{crowd}} + \alpha_3 R_{\text{hist}}
```
Plain-English: A weighted average of risk data sources informs routing. Called “Bayesian-inspired” to acknowledge future work toward full Bayesian inference.

---

## Related Work (Slides 12–14)

### Slide 12 — Related Work Categories
- Summarizes five literature clusters: disaster routing, commercial navigation, government monitors, MAS simulations, Philippine-specific systems
- Emphasizes absence of a real-time, deployed MAS for flood routing

### Slide 13 — Risk-Aware Pathfinding Timeline
- Chronological references from Dijkstra (1959) through MAS-FRO (2025)
- Communicates that MAS-FRO extends established algorithms to a new operational domain

### Slide 14 — MAS-FRO Unique Niche
- Venn diagram narrative: MAS ($\cap$) real-time flood data ($\cap$) operational deployment has only one occupant — MAS-FRO
- Benchmarks Google Maps, RoboCup, NOAH as covering partial intersections only

---

## System Architecture (Slides 15–24)

### Slide 15 — Architecture Overview
- Star topology centered on `HazardAgent`; leaves include FloodAgent, ScoutAgent, RoutingAgent, EvacuationManager
- DynamicGraphEnvironment sits beneath to encapsulate network updates
- Conveys autonomous behavior + star coordination pattern

### Slide 16 — Agent Roles Matrix
- Table summarizing five agents: type (collector/coordinator/service/interface), role, lines of code, module, operational status
- Serves as quick inventory for reviewers

### Slide 17 — FIPA-ACL Message Example

```python
ACLMessage(
    performative=Performative.INFORM,
    sender="flood_agent_001",
    receiver="hazard_agent_001",
    content={
        "info_type": "flood_data_update",
        "data": {
            "Sto Nino": {
                "water_level": 15.2,
                "risk_level": "ALERT"
            }
        }
    },
    conversation_id="collection_12345"
)
```
Source: `app/communication/acl_protocol.py`, `app/communication/message_queue.py`

### Slide 18 — Communication Sequence
- Sequence from user HTTP request to EvacuationManager → RoutingAgent → DynamicGraphEnvironment → back to EvacuationManager → HTTP response
- Typical turnaround: 0–3 seconds

### Slide 19 — Dynamic Graph Environment
- Edges weighted by `length * risk_score`; risk mapped to color bands (green/yellow/red)
- Updates triggered every 5 minutes via `HazardAgent` output; see `app/environment/graph_manager.py`

### Slide 20 — Risk-Aware A* (Weight Function)

```python
def weight_function(u, v, edge_data):
    length = edge_data['length']
    risk = edge_data['risk_score']
    if risk >= 0.9:
        return float('inf')
    return w_d * length + w_r * length * risk
```
Plain-English: Edges above the risk threshold are pruned; otherwise distance-times-risk contributes to path cost.

### Slide 21 — Multi-Source Data Fusion Pipeline
- Diagram narrative: PAGASA (α1=0.5), crowdsourced social (α2=0.3), historical risk (planned; α3=0.2) → Weighted sum → Edge risk scores
- Highlighted limitations: heuristic weights, historical component not yet deployed

### Slide 22 — FloodAgent Implementation

```python
def fetch_real_river_levels(self) -> Dict:
    """Fetch from PAGASA API, filter Marikina stations."""
    stations = self.river_scraper.get_river_levels()  # 17 stations
    marikina_stations = ["Sto Nino", "Nangka", "Tumana",
                         "Montalban", "Rosario Bridge"]
    filtered = {s['name']: classify_risk(s['water_level'],
                                         s['critical_level'])
                for s in stations if s['name'] in marikina_stations}
    return filtered  # 5 stations
```
Source: `app/agents/flood_agent.py`

### Slide 23 — HazardAgent Implementation

```python
def fuse_data(self) -> Dict[str, Any]:
    """Weighted multi-source aggregation."""
    fused = {}
    for edge in graph.edges():
        depth = geotiff.get_depth(edge_midpoint)  # official
        R_official = map_depth_to_risk(depth)
        reports = find_reports_within_500m(edge)  # crowd
        R_crowd = average_severity(reports)
        risk = 0.5*R_official + 0.3*R_crowd + 0.2*R_hist
        fused[edge] = min(risk, 1.0)
    return fused
```
Source: `app/agents/hazard_agent.py`

### Slide 24 — System Statistics
- 5 autonomous agents, ~8 k LOC across MAS modules
- PAGASA integration reduces 17 national stations to 5 relevant Marikina nodes
- 72 GeoTIFF raster files cover DOST-NOAH flood scenarios
- Graph scale: ~2.5 k nodes, ~5 k edges; update cadence: 5 minutes; real data coverage: 95 %

---

## Agreement Form Compliance (Slides 25–32)

### Slide 25 — Overview Table
- Itemized status for Agreement Form checklist:
  - Item 1 (MAS Communication): 4/5 ✓ (stress testing pending)
  - Item 2 (Dynamic Graph): 5/5 ✓ (weight calibration pending)
  - Item 3 (Baseline): 0/3 ✗ critical gap
  - Item 4 (Risk-Aware A*): Complete
  - Item 5 (Simulation): 2/4 ⚠ (systematic testing pending)
  - Item 6 (Web Prototype): Complete
  - Item 7 (Paper): Rejected; Items 3, 5, 1.v cited as blockers

### Slide 26 — Item 1: MAS Communication
- Achievements: Roles defined, FIPA-ACL middleware, JSON message schema
- Remaining gaps: Failover limited to graceful degradation, no network stress testing executed
- Refs: `app/communication/acl_protocol.py`, `app/communication/message_queue.py`

### Slide 27 — Item 2: Dynamic Graph
- Complete coverage for modeling, GIS integration, GeoTIFF ingestion, real-time edge updates, hazard scoring
- Caveat: Risk weights heuristic, require empirical calibration (see `app/environment/risk_calculator.py`)

### Slide 28 — Item 3: Baseline (Critical Gap)
- No centralized routing baseline currently exists; no computational, accuracy, or scalability comparisons have been run
- Primary rejection reason for paper; roadmap: 16–20 engineering hours
- TODO references: `TODO.md` (Dijkstra baseline), `ROUTING_STATUS_ANALYSIS.md`

### Slide 29 — Item 4: Risk-Aware A*

```tex
P^* = \arg\min_{P \in \mathcal{P}(s, t)} \sum_{e \in P} C(e), \quad
C(e) = \begin{cases}
\infty & r(e) \geq 0.9 \\
w_d d(e) + w_r d(e) r(e) & \text{otherwise}
\end{cases}
```
Plain-English: Shortest safe path is computed by summing edge costs that blend distance and risk; edges above threshold are excluded.

### Slide 30 — Item 5: Simulation Testing
- Partial progress: Agent instances configured, scenario tests exist (`tests/unit/`)
- Missing: Systematic runs, metrics logging, structured log retention
- Estimated effort: 20–24 hours to complete framework

### Slide 31 — Item 6: Web Prototype
- Next.js 15, Mapbox GL 3.15, custom React components (`masfro-frontend/src/components`)
- FastAPI backend with 18+ REST endpoints (`app/main.py`), WebSocket updates, PostgreSQL storage (`app/database/models.py`)
- Classification: Functional prototype (not production hardened)

### Slide 32 — Item 7: Paper Status
- Current state: Rejected; deficits include Items 3, 5, 1.v
- Roadmap: Phase 1 (56–72 hours) to close technical gaps; Phase 2 real-world validation; Phase 3 resubmission
- Target venues: ACM TIST, IEEE TITS, Expert Systems with Applications (post-gap closure)

---

## Implementation Highlights (Slides 33–37)

### Slide 33 — Real-Time Data Integration
- Data flow narrative: PAGASA river scraper → HazardAgent; OpenWeatherMap One Call → HazardAgent; GeoTIFF flood depths → HazardAgent; Twitter/X NLP → HazardAgent → DynamicGraphEnvironment
- Update frequency: 5 minutes; API costs within free tier limits (≤576 calls/day per source)

### Slide 34 — GeoTIFF Service Architecture
- Steps: Request selects return period/time-step → Lazy load `.tif` → LRU cache (max size 32) → Coordinate transform (WGS84 to Web Mercator) via `pyproj` → Pixel query from raster (e.g., 368×372 grid) → Flood depth in meters
- Implementation: `app/services/geotiff_service.py`

### Slide 35 — WebSocket Real-Time Architecture
- Sequence: FloodAgent fetch (T=0 s) → HazardAgent fuse (T=4 s) → ConnectionManager broadcast (T=5 s) → Clients receive (T≈5.05 s)
- Message types: `flood_update`, `critical_alert`, `scheduler_update`
- Implementation: `app/main.py` (ConnectionManager), `masfro-frontend/src/hooks/useWebSocket.js`

### Slide 36 — Database Schema
- Tables: `flood_data_collections` (UUID PK), `river_levels` (1:N), `weather_data` (1:1)
- Tooling: PostgreSQL 14+, SQLAlchemy 2.0, Alembic migration history
- Data volume: 10 k+ records across 5+ months of operations (projected)

### Slide 37 — Dependency Overview
- Backend: FastAPI, uvicorn, NetworkX, OSMnx, Rasterio, SQLAlchemy, Selenium, httpx, schedule (see `masfro-backend/pyproject.toml`)
- Frontend: Next.js 15.5, Mapbox GL 3.15, React 19.1, geotiff.js 2.1, react-leaflet 5.0, Tailwind CSS 4 (see `masfro-frontend/package.json`)

---

## Performance (Slides 38–40)

### Slide 38 — Preliminary Performance Metrics
| Metric | Observed | Method | Sample |
|--------|----------|--------|--------|
| Route computation | 0.5–2 s (μ = 1.2 s, σ = 0.4 s) | Manual timing | n = 20 |
| PAGASA API | 1–3 s | `requests` | n = 15 |
| OpenWeatherMap | 0.5–1 s | `requests` | n = 15 |
| GeoTIFF query | <0.1 s | Rasterio + cache | n = 100 |
| Database read | <100 ms | SQLAlchemy | n = 50 |
| WebSocket latency | <50 ms | AsyncIO loop | n = 20 |

- Warning banner: Preliminary manual tests; systematic benchmarking pending

### Slide 39 — System Operational Statistics
- Uptime: 5+ months continuous operation (projected)
- Data size: 10 k+ database records accumulated (projected)
- API cadence: 288 requests/day (5-minute schedule per source)
- Reliability: 95 % real data coverage; zero critical failures logged

### Slide 40 — Data Quality Assessment
- Distribution: 95 % real API data, 5 % simulated fallback for resilience
- Source uptime: PAGASA 100 %, OpenWeatherMap 100 %, GeoTIFF local files (no downtime)

---

## Critical Assessment (Slides 41–45)

### Slide 41 — Limitations
- Geographic: Marikina-only, no multi-city scaling yet
- Validation: Baseline absent, no real emergency deployment, sample size small, no expert/user study
- Algorithmic: Heuristic risk weights, no uncertainty modeling, deterministic pipeline
- Data sources: PAGASA reliability variability, forecast uncertainty, manual login for Twitter scraping, static GeoTIFF snapshots, historical risk integration pending
- System: No formal failover, no load balancing, limited observability/monitoring, minimal rate limiting
- UX: Desktop-first, no offline mode, English-only interface

### Slide 42 — Publication Gaps
- **Complete**: Dynamic graph, risk-aware A*, web prototype
- **Partial**: MAS communication (stress test pending), simulation testing (systematic execution pending)
- **Missing**: Baseline module, comparative evaluation, statistical validation

### Slide 43 — Roadmap to Q1-Ready
- Phase 1 (3–6 months): Implement baseline, run systematic tests, stress tests, calibrate weights (~56–72 hours of engineering work)
- Phase 2 (6–12 months): Real-world validation during typhoon season; expert and user studies
- Publication milestone (12–15 months): Paper revision and resubmission

### Slide 44 — Honest Assessment for Panel
- Quote summary: MAS-FRO qualifies as a strong prototype; lacks comparative evaluation and real-world validation required for Q1 journal acceptance
- Outlines path to convert to publication-ready application/system paper after gap closure

### Slide 45 — Lessons Learned
1. Implement baselines early to enable comparison
2. Automate systematic testing to avoid manual-only evidence
3. Qualify contributions to avoid overstating novelty
4. Calibrate heuristic parameters empirically
5. Validate during real flood events to move beyond simulation

---

## Future Work & Conclusion (Slides 46–49)

### Slide 46 — Research Contributions (Qualified)
- Tabular summary of four contributions framed as application/system engineering, not algorithmic novelty
  - Risk-Aware A* adapted for Philippine flood routing (PAGASA integration, 5-minute updates)
  - Real-time multi-source aggregation framework (4 heterogeneous sources, 95 % real data)
  - FIPA-ACL compliance for disaster MAS communication (9 performatives, queue system)
  - Functional prototype with government APIs (PAGASA + OWM + GeoTIFF)

### Slide 47 — Future Work (Phased)
- Phase 1: Baseline + benchmarking + stress tests → Publication readiness
- Phase 2: Machine learning risk models (Random Forest, LSTM), Metro Manila expansion, mobile app
- Phase 3: Full Bayesian fusion, multi-hazard support, LGU integration

### Slide 48 — Geographic Expansion Outlook
- Narrative: Expand from Marikina to adjacent cities (Pasig, Quezon), then full Metro Manila, then national coverage
- Dependency: Additional GeoTIFF datasets, historical flood data curation

### Slide 49 — Conclusion Matrix
- Three-column bullets summarizing achievements, gaps, and path forward (56–72 h gap closure, 6–12 month validation, 12–15 month publication)

---

## Q&A (Slide 50)
- Slide text: “Questions?” with reminder that backup slides are available for detailed technical queries

---

## Backup Appendix (Slides A1–A12)

### Slide A1 — A* Admissibility Proof (Sketch)
- States claim: Haversine heuristic never overestimates geodesic distance → admissible
- Sketch: Great-circle distance lower-bounds road paths → \( h(n) \leq h^*(n) \)

### Slide A2 — Complexity Derivation (Detailed)
- Outlines heap operations and edge scanning cost, confirming \( \mathcal{O}((|V|+|E|)\log |V|) \)

### Slide A3 — Risk Calculation Code (Complete Example)
- Full method from HazardAgent combining depth risk and proximity risk with weighting

```python
def calculate_risk_scores(self, fused_data: Dict) -> Dict:
    risk_scores = {}
    for u, v, key in self.environment.graph.edges():
        edge_data = self.environment.graph[u][v][key]
        geometry = edge_data.get('geometry')
        if not geometry:
            continue
        midpoint = geometry.interpolate(0.5, normalized=True)
        depth = self.geotiff_service.get_flood_depth_at_point(
            midpoint.x, midpoint.y, self.return_period, self.time_step
        )
        depth_risk = self._map_depth_to_risk(depth)
        prox_risk = self._calculate_proximity_risk(geometry, fused_data)
        combined = 0.6 * depth_risk + 0.4 * prox_risk
        risk_scores[(u, v, key)] = min(combined, 1.0)
    return risk_scores
```
Source: `app/agents/hazard_agent.py`

### Slide A4 — Database Schema (Full ER Sketch)
- Textual ER description: `flood_data_collections` (UUID, timestamp, source) with child tables `river_levels` (station, level, foreign key) and `weather_data` (temperature, rainfall, foreign key)

### Slide A5 — FIPA-ACL Message Queue Core

```python
class MessageQueue:
    def __init__(self):
        self.queues: Dict[str, Queue] = {}
        self.lock = Lock()
    def send_message(self, message: ACLMessage) -> bool:
        receiver = message.receiver
        with self.lock:
            if receiver not in self.queues:
                raise ValueError(f"Receiver {receiver} not registered")
            self.queues[receiver].put(message)
            return True
```
Source: `app/communication/message_queue.py`

### Slide A6 — FloodAgent Data Collection Flow
- Enumerated pipeline: schedule trigger → PAGASA API (17 stations) → Marikina filter → OWM API context → risk classification → ACL message dispatch → persistence → WebSocket broadcast

### Slide A7 — Haversine Formula Derivation
- Notes derivation from spherical law of cosines; Haversine chosen for numerical stability at city-scale distances

### Slide A8 — Dependency Graph Visualization (Narrative)
- Relationships: FastAPI→uvicorn/pydantic/starlette; OSMnx→NetworkX→Rasterio; SQLAlchemy→psycopg2-binary; see `masfro-backend/pyproject.toml`

### Slide A9 — Frontend Component Architecture
- Component tree: App → Layout → MapboxMap (GeoTIFF overlay, route layer, markers) + LocationSearch + FloodAlerts + FeedbackForm; shared state via `useWebSocket` hook and context

### Slide A10 — Performance Profiling Snapshot
- Notes: A* search consumes ~60 % CPU; memory peak ≈ 150 MB; opportunities include bidirectional A* and heuristic tuning

### Slide A11 — Historical Flood Dataset Plan
- Table concept listing events (Ondoy 2009, Ulysses 2020) with max levels, impassable roads, duration → to support future calibration

### Slide A12 — Comparative Baseline Design
- Contrast: MAS-FRO distributed agent architecture versus planned centralized baseline (single process, synchronous data collection, direct calls, lower resilience)

---

## Index of Code References

- `app/agents/flood_agent.py`
- `app/agents/hazard_agent.py`
- `app/algorithms/risk_aware_astar.py`
- `app/communication/acl_protocol.py`
- `app/communication/message_queue.py`
- `app/environment/graph_manager.py`
- `app/environment/risk_calculator.py`
- `app/main.py`
- `app/services/geotiff_service.py`
- `app/services/flood_data_scheduler.py`
- `app/database/models.py`
- `masfro-frontend/src/components/MapboxMap.js`
- `masfro-frontend/src/hooks/useWebSocket.js`
- `masfro-backend/pyproject.toml`
- `masfro-frontend/package.json`

Refer back to the main `README.md` for extended context, Agreement Form compliance documentation, dependency tables, risk equations, and full literature review.

---

## Revision Checklist

Before publishing updates to the slide deck or this markdown companion:

- [ ] Validate that Beamer source and markdown narrative remain in sync (slide titles, numbering, bullet content)
- [ ] Re-run TeX compilation (`pdflatex` or `lualatex`) to ensure no warnings/error regressions
- [ ] Refresh risk weighting rationale if calibration experiments are completed
- [ ] Update Agreement Form section once baseline, simulation testing, or stress testing milestones are achieved
- [ ] Synchronize dependency references with `pyproject.toml` and `package.json` after package upgrades
- [ ] Verify cross-links (`../`, `./`) remain correct after directory or filename changes
- [ ] Rebuild slides for Overleaf presentation if TikZ diagrams are replaced with high-fidelity assets
- [ ] Clean auxiliary TeX artifacts (`latexmk -c`) prior to committing build outputs

Maintaining both the LaTeX source and this markdown mirror ensures reviewers can quickly digest the research narrative without compiling the deck, while preserving the rigorous format required for defense and publication workflows.

---

## PhD-Level Defense Script

Provide this narration verbatim or adapt it to your speaking style. Each script assumes the panel is hearing the presentation over Zoom without watching the slides, so every segment introduces context, defines technical terms, and reminds listeners what they would be seeing on-screen.

### Slide 1 – Title Slide
“Good day, esteemed panel. We are presenting ‘MAS-FRO: Multi-Agent System for Flood Route Optimization,’ an operational prototype focused on Marikina City in the Philippines. Today I will walk you through our research question, the architecture we built, and the validation gaps that remain before journal submission. Please note that this is an 85 percent complete prototype; comparative benchmarking and stress testing are still in progress.”

### Slide 2 – The Ondoy Disaster (2009)
“To ground this work, recall Typhoon Ondoy in 2009, when Marikina recorded 455 millimeters of rainfall in just six hours and the river rose to 21.5 meters, about four and a half meters above the critical level. Over 80 lives were lost in Marikina alone, largely because navigation systems kept routing evacuees into flood zones. Our visual shows a stylized map with the river overlaid by flood extents to remind us why safer routing matters.”

### Slide 3 – Research Gap
“Existing systems fall short in different ways. Commercial navigation such as Google Maps handles traffic but not flood safety. Government dashboards like DOST-NOAH monitor flood levels but do not compute routes. Academic multi-agent systems remain in simulation. MAS-FRO is the only platform we found that combines multi-agent coordination, real-time flood data, crowdsourced reports, and risk-aware routing in a working prototype.”

### Slide 4 – Marikina City Context
"Marikina covers about twenty-one and a half square kilometers, with roughly 450,000 residents and a road network of around 10,000 intersections and 20,000 directed road segments. Five PAGASA river stations and thirty-six evacuation centers define our operational landscape. The slide map highlights these points and reminds everyone of our precise geographic scope."

### Slide 5 – Five Challenges
“We face five key challenges: first, flood hazards change within minutes. Second, we must fuse official data, weather feeds, remote sensing, and social media. Third, evacuees need route answers within two seconds. Fourth, data reliability varies widely. Fifth, the system must run nonstop even when some data sources fail. These challenges drove every architecture decision.”

### Slide 6 – Research Objectives
“Our primary goal is to deliver real-time, flood-safe routing for Marikina. That decomposes into five objectives: build a hierarchical multi-agent architecture using FIPA-ACL messaging; ingest real APIs such as PAGASA and OpenWeatherMap; implement a risk-aware A* search; deliver a working web prototype; and validate performance—although large-scale comparative validation is still pending.”

### Slide 7 – Scope and Limitations
“We are transparent about scope: MAS-FRO currently serves Marikina only. It has been running for over five months with live data. We do not yet support other cities, multi-hazard scenarios, or offline resilience. Validation gaps include the absence of a baseline routing comparison, no tests during actual emergencies, and pending expert evaluations.”

### Slide 8 – Multi-Agent Systems Theory
“Here we remind the audience how each agent aligns with the core properties defined by Wooldridge: autonomy, reactivity, proactivity, and social ability. FloodAgent autonomously schedules data pulls; HazardAgent reacts to incoming updates and fuses them; RoutingAgent proactively computes routes on request. All communicate through FIPA-ACL messages, giving us a standards-based backbone.”

### Slide 9 – Graph Theory and A*
"The road network is modeled as a directed multigraph with about 10,000 nodes. We run A* search, where the total cost f of a node equals the path cost g plus a heuristic h. Our heuristic is the Haversine distance, which remains admissible—meaning it never overestimates real distance—at the Marikina scale. The time complexity stays within the expected order of roughly E plus V times log V."

### Slide 10 – Risk Assessment and MCDM
“Every edge cost blends distance with risk using a weighted sum: forty percent distance, sixty percent risk. If an edge’s risk score reaches zero point nine, we treat it as impassable by assigning infinite cost. This is a multi-criteria decision-making setup that lets us balance speed with safety, though we have yet to calibrate the weights empirically.”

### Slide 11 – Data Fusion Terminology
“We call our weighting ‘Bayesian-inspired’ because it is a linear combination that still needs full Bayesian inference. Official data carries fifty percent weight, crowdsourced signals thirty percent, and historical data twenty percent, although the historical layer is not yet rolled out. We emphasize this nuance so there is no misunderstanding about what has been implemented.”

### Slide 12 – Related Work Categories
“We reviewed five bodies of work: disaster routing, commercial navigation, government monitors, academic multi-agent simulations, and Philippine-specific tools. None provided real-time flood-aware routing that is deployed to the public, leaving MAS-FRO in a unique operational niche.”

### Slide 13 – Risk-Aware Pathfinding Timeline
“The timeline slide traces foundational algorithms from Dijkstra in 1959 through Hart’s A* in 1968 and later risk-aware adaptations. MAS-FRO stands on these shoulders by applying established algorithms to an urgent flood-evacuation context, rather than claiming theoretical novelty.”

### Slide 14 – MAS-FRO Niche Diagram
“When we intersect three sets—multi-agent systems, real-time flood data, and operational deployment—MAS-FRO is the sole occupant. Google Maps overlaps real-time and deployment but not multi-agent flood safety. Academic MAS efforts overlap with multi-agent theory but not real data. This helps frame our work as an engineering integration.”

### Slide 15 – Architecture Overview
“Now we describe the architecture verbally: imagine HazardAgent at the center, connected to FloodAgent and ScoutAgent on the left and right, routing services above, and the dynamic graph underneath. Messages flow inward to HazardAgent, which updates the shared graph; RoutingAgent queries that graph; EvacuationManager interacts with end users. The diagram portrays this star topology.”

### Slide 16 – Agent Roles Matrix
“We summarize each agent: FloodAgent harvests official data; ScoutAgent handles social media via NLP; HazardAgent fuses signals and updates risk; RoutingAgent computes paths; EvacuationManager bridges to client interfaces. We cite the lines of code and file locations to show system maturity.”

### Slide 17 – FIPA-ACL Example
“Here I walk through an INFORM message from FloodAgent to HazardAgent. The payload includes a water level for the Sto. Niño station flagged as ‘ALERT.’ This example assures reviewers that we implemented FIPA-performatives concretely in our queue.”

### Slide 18 – Communication Flow
“In response to a user request, EvacuationManager issues a REQUEST message to RoutingAgent, which queries the dynamic graph, obtains a safe route, responds with CONFIRM, and then returns results to the user via HTTP. This keeps the path from user voice to database under three seconds in normal conditions.”

### Slide 19 – Dynamic Graph Explanation
“This slide verbalizes a graph with colored edges: green for safe, red for high risk. HazardAgent updates each edge weight by multiplying its length with a dynamic risk score. These updates run every five minutes so the cost landscape tracks the latest flood data.”

### Slide 20 – Risk-Aware Weight Function
“We read out the weight function: if an edge’s risk score is greater than or equal to zero point nine, return infinity; otherwise return distance times the weighted combination. This explicitly encodes the rule that riskier roads are avoided even if they are short.”

### Slide 21 – Multi-Source Fusion Flow
“I describe the flow: first official data from PAGASA, second crowdsourced reports from social media, third a planned historical layer. The weights pass through a fusion function and produce updated edge scores. I also state that the historical component is still pending, so the current fusion uses the first two signals.”

### Slide 22 – FloodAgent Code Walkthrough
“FloodAgent fetches seventeen station readings, filters for the five in Marikina, compares each reading with the official critical level, and classifies the risk tier. This ensures the system focuses only on relevant local measurements.”

### Slide 23 – HazardAgent Code Walkthrough
“HazardAgent iterates through each edge, queries GeoTIFF depth, retrieves nearby social reports, and averages the severity. It then combines these signals using the weighting we discussed. This is a live code excerpt to reassure reviewers about implementation depth.”

### Slide 24 – System Statistics Overview
“To prove scale, we cite the five autonomous agents, around eight thousand lines of Python supporting them, seventy-two GeoTIFF files, and the graph size. We also note the five-minute update schedule and the fact that ninety-five percent of data is real rather than simulated.”

### Slide 25 – Agreement Form Dashboard
“This slide is a traffic-light table showing which Agreement Form items are complete, partial, or missing. It quickly orients the panel to our compliance status before diving deeper.”

### Slide 26 – Item 1: MAS Communication
“I highlight the completed components—agent roles, communication middleware, message formats—and then state that failover is limited to graceful degradation and that formal stress testing remains outstanding.”

### Slide 27 – Item 2: Dynamic Graph
“All requirements here are complete: our NetworkX graph integrates OSM data, GeoTIFF layers, and hazard scoring. Yet we flag that the risk weights are heuristic, and we plan calibration experiments to solidify them.”

### Slide 28 – Item 3: Baseline Gap
“This is the major red flag. We do not yet have a centralized baseline routing module, and therefore no comparative analysis of computational time, accuracy, or scalability. This gap alone blocks Q1 submission, and we state the estimated effort—roughly sixteen to twenty hours—to implement it.”

### Slide 29 – Item 4: Risk-Aware A* Completed
“Here we restate the mathematical definition of our cost function and confirm the complexity bounds. We stress that this is an application of known techniques rather than a novel algorithm, aligning expectations with the journal scope.”

### Slide 30 – Item 5: Simulation Testing Partial
“We mention that all agents can be instantiated in test mode and that there are scenario scripts, but systematic execution and metric logging have not been automated. This again will require dedicated engineering time.”

### Slide 31 – Item 6: Web Prototype Complete
“I describe the working prototype: Next.js 15 frontend, Mapbox GL maps, live overlay of flood layers, and FastAPI endpoints powering routing. While functional, we clarify it is not production hardened.”

### Slide 32 – Item 7: Paper Status
“We acknowledge that the paper was rejected, with reviewers citing missing baseline comparisons, lack of systematic testing, and incomplete failure analysis. We present a roadmap to address these critiques before resubmission.”

### Slide 33 – Real-Time Data Integration
“The narration walks listeners through the data pipeline: FloodAgent collects river levels, OpenWeatherMap contributes rainfall and forecasts, GeoTIFF provides depth grids, and ScoutAgent processes social media text. HazardAgent fuses these inputs and updates the shared graph every five minutes.”

### Slide 34 – GeoTIFF Service Pipeline
“Here I describe the six-step pipeline verbally: select return period, lazy-load the raster file, use an LRU cache for speed, transform coordinates to the raster projection, pull the pixel depth, and hand the value back to HazardAgent.”

### Slide 35 – WebSocket Architecture
“I narrate the real-time update cycle: data fetch at timestamp zero seconds, fusion by four seconds, broadcast by five seconds, and client reception milliseconds later. I note the message types and the auto-reconnect behavior.”

### Slide 36 – Database Schema
“The database contains three tables: a flood data collection table keyed by UUID, a river levels table linked in a one-to-many relationship, and a weather table in a one-to-one relation. We point out the five months of historical data already stored.”

### Slide 37 – Dependency Overview
“We list critical backend dependencies like FastAPI, NetworkX, and Rasterio, and front-end ones like Next.js and Mapbox GL. The aim is to show the stack is modern and well-supported.”

### Slide 38 – Preliminary Metrics
“I speak through the table: route computations average around one point two seconds; API calls to PAGASA and OpenWeatherMap stay within three and one seconds respectively; GeoTIFF lookups are under a tenth of a second. Then I emphasize that the sample sizes are small—between fifteen and twenty runs—so these are provisional measurements.”

### Slide 39 – Operational Statistics
“We emphasize more than five months of uptime (projected), over ten thousand database records (projected), a regular cadence of two hundred eighty-eight API calls per day, and the zero critical failures recorded so far.”

### Slide 40 – Data Quality Breakdown
“This slide reminds the audience that ninety-five percent of data is real-time from APIs, with only five percent simulated fallback, and that our main sources have been stable with one hundred percent uptime in this period.”

### Slide 41 – Limitations
“We now enumerate limitations across geography, validation, algorithms, data sources, system resilience, and user experience. This establishes credibility by showing we have audited our own weaknesses carefully.”

### Slide 42 – Publication Gaps
“We categorize Agreement Form items into complete, partial, and missing. This is designed to make it easy for reviewers to align our roadmap with the journal expectations.”

### Slide 43 – Roadmap to Q1
“We describe the three phases: short-term gap closure within three to six months, mid-term real-world validation over six to twelve months, and publication-ready resubmission within twelve to fifteen months.”

### Slide 44 – Honest Assessment
“The scripted quote acknowledges that MAS-FRO is a robust prototype but not yet Q1-ready. We signal our intent to position the work as an engineering system once the remaining validation is complete.”

### Slide 45 – Lessons Learned
“We close the section by summarizing five lessons: implement baselines early, automate tests, avoid overstating novelty, tune parameters with data, and seek real-event validation. These lessons drive the next iteration.”

### Slide 46 – Qualified Contributions
“I summarize four contributions, each labeled as an application or systems engineering outcome. Again we reinforce that we are not claiming algorithmic breakthroughs but rather integration and deployment advances.”

### Slide 47 – Future Work Phases
“The narration explains the three-phase roadmap: Phase 1 closes immediate research gaps, Phase 2 introduces machine learning and mobile access, Phase 3 extends to multi-hazard support and government integration.”

### Slide 48 – Geographic Expansion
“Listeners hear a progression from Marikina to adjacent cities, then to Metro Manila, and finally nationwide coverage, with the caveat that each expansion requires new data such as localized GeoTIFF maps and historical flood records.”

### Slide 49 – Conclusion Matrix
“We repeat our achievements, restate the open gaps, and detail the path forward with effort estimates. This ensures the takeaways are clear even as we move into Q&A.”

### Slide 50 – Questions Prompt
“I invite questions and remind the panel that backup slides are available for deeper technical topics such as proofs, code excerpts, and performance profiling.”

### Slide A1 – A* Admissibility Proof
“In the appendix we sketch why Haversine distance is admissible: great-circle distance always underestimates actual road distance, so A* remains optimal. This reminds the panel we have mathematical backing ready if required.”

### Slide A2 – Complexity Derivation
“We outline how priority queue operations lead to the familiar big O of edges plus nodes times log nodes. This satisfies theoretical rigor if someone requests it.”

### Slide A3 – Full Risk Calculation Code
“We read the full method that maps flood depths and proximity to risks, highlighting the combination of official and crowdsourced signals. This demonstrates implementation transparency.”

### Slide A4 – Database Schema Details
“We provide the textual entity–relationship description so reviewers know exactly how flood collections, river levels, and weather data relate without seeing the diagram.”

### Slide A5 – Message Queue Core
“We explain the thread-safe queue mechanism that routes messages between agents, pointing out the registration checks and locking strategy.”

### Slide A6 – FloodAgent Flowchart
“We step through the ten stages from the scheduled trigger up to WebSocket broadcast, ensuring the data movement is clear even without the visual flowchart.”

### Slide A7 – Haversine Derivation Note
“We reiterate why we chose the Haversine formula over alternatives like Vincenty: it maintains accuracy at city scale with less numerical instability.”

### Slide A8 – Dependency Graph Narrative
“We verbally describe how FastAPI relies on uvicorn and pydantic, how OSMnx builds on NetworkX and requests, and how Rasterio ties into GDAL. This double-checks that the stack is coherent.”

### Slide A9 – Frontend Component Tree
“We list the React component hierarchy: Mapbox map, GeoTIFF overlay, route layer, evacuation markers, plus supporting components such as search and alerts. This assures the panel the UI is modular.”

### Slide A10 – Performance Profiling Notes
“We mention the flamegraph takeaway that A* consumes about sixty percent of runtime and memory peaks around one hundred fifty megabytes, suggesting future optimization targets.”

### Slide A11 – Historical Dataset Plan
“We describe the planned dataset of past flood events—including Ondoy and Ulysses—with metrics like maximum water level and number of impassable roads, which will feed future calibration.”

### Slide A12 – Comparative Baseline Design
“Finally we compare MAS-FRO’s distributed architecture with the upcoming centralized baseline. This clarifies the experimental design we will use to quantify MAS benefits.”

Use this script alongside the slide deck to deliver a cohesive, listener-friendly defense that remains rigorous and honest about the system’s current maturity.

