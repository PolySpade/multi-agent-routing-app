╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌
 Implementation Plan: masfro-backend-v2

 Overview

 Create a new masfro-backend-v2/ folder implementing the MAS-FRO backend based on BACKEND_IMPLEMENTATION.md, with the key enhancement being Qwen 
  3 LLM Integration (Section 13).

 Approach

 Copy and Refactor - The existing masfro-backend/ is production-ready. We will:
 1. Copy stable components (algorithms, database, communication)
 2. Refactor agents to add LLM capabilities
 3. Create new LLM service for centralized Qwen 3 integration

 Directory Structure

 masfro-backend-v2/
 ├── app/
 │   ├── __init__.py
 │   ├── main.py                          # FastAPI entry (add LLM health endpoint)
 │   ├── agents/
 │   │   ├── base_agent.py               # Copy
 │   │   ├── flood_agent.py              # Refactor: add parse_text_advisory()
 │   │   ├── scout_agent.py              # Refactor: add Qwen 3 + Qwen 3-VL
 │   │   ├── hazard_agent.py             # Refactor: add Visual Override
 │   │   ├── routing_agent.py            # Copy
 │   │   └── evacuation_manager_agent.py # Copy
 │   ├── algorithms/                      # Copy entire folder
 │   ├── api/                             # Copy entire folder
 │   ├── communication/                   # Copy entire folder
 │   ├── core/
 │   │   ├── config.py                   # Refactor: add LLM settings
 │   │   ├── agent_config.py             # Refactor: add LLMConfig
 │   │   └── ... (copy rest)
 │   ├── data/                            # Copy (symlink GeoTIFFs)
 │   ├── database/                        # Copy entire folder
 │   ├── environment/                     # Copy entire folder
 │   ├── ml_models/                       # Copy (fallback NLP)
 │   ├── models/                          # Copy entire folder
 │   ├── services/
 │   │   ├── llm_service.py              # NEW: Qwen 3 integration
 │   │   └── ... (copy rest)
 │   └── utils/                           # Copy
 ├── config/
 │   ├── agents.yaml                     # Refactor: add llm_service section
 │   └── default.yaml                    # Copy
 ├── data/
 │   └── marikina_graph.graphml          # Copy
 ├── alembic/                             # Copy entire folder
 ├── tests/                               # Copy + add LLM tests
 ├── .env.example                         # Refactor: add LLM env vars
 ├── pyproject.toml                       # Refactor: add ollama dependency
 └── README.md                            # New

 Implementation Phases

 Phase 1: Foundation
 ┌────────────────────────────┬────────────────────────────────┬─────────────────────────────────────────┐
 │            Task            │             Action             │                  Files                  │
 ├────────────────────────────┼────────────────────────────────┼─────────────────────────────────────────┤
 │ Create directory structure │ Create                         │ All folders                             │
 ├────────────────────────────┼────────────────────────────────┼─────────────────────────────────────────┤
 │ Project config             │ Copy + add ollama>=0.4.0       │ pyproject.toml                          │
 ├────────────────────────────┼────────────────────────────────┼─────────────────────────────────────────┤
 │ Environment config         │ Copy + add LLM vars            │ .env.example                            │
 ├────────────────────────────┼────────────────────────────────┼─────────────────────────────────────────┤
 │ Core config                │ Copy + add LLM settings        │ app/core/config.py                      │
 ├────────────────────────────┼────────────────────────────────┼─────────────────────────────────────────┤
 │ Agent config               │ Copy + add LLMConfig           │ app/core/agent_config.py                │
 ├────────────────────────────┼────────────────────────────────┼─────────────────────────────────────────┤
 │ YAML config                │ Copy + add llm_service section │ config/agents.yaml, config/default.yaml │
 └────────────────────────────┴────────────────────────────────┴─────────────────────────────────────────┘
 Phase 2: Copy Unchanged Components
 ┌───────────────┬──────────────────────────────────────────────────────────────────────────┐
 │   Component   │                                  Files                                   │
 ├───────────────┼──────────────────────────────────────────────────────────────────────────┤
 │ Communication │ app/communication/acl_protocol.py, message_queue.py                      │
 ├───────────────┼──────────────────────────────────────────────────────────────────────────┤
 │ Algorithms    │ app/algorithms/risk_aware_astar.py, path_optimizer.py, baseline_astar.py │
 ├───────────────┼──────────────────────────────────────────────────────────────────────────┤
 │ Database      │ app/database/models.py, repository.py, connection.py                     │
 ├───────────────┼──────────────────────────────────────────────────────────────────────────┤
 │ Environment   │ app/environment/graph_manager.py, risk_calculator.py                     │
 ├───────────────┼──────────────────────────────────────────────────────────────────────────┤
 │ API routes    │ app/api/ entire folder                                                   │
 ├───────────────┼──────────────────────────────────────────────────────────────────────────┤
 │ ML models     │ app/ml_models/ entire folder (fallback NLP)                              │
 ├───────────────┼──────────────────────────────────────────────────────────────────────────┤
 │ Services      │ All except llm_service.py                                                │
 ├───────────────┼──────────────────────────────────────────────────────────────────────────┤
 │ Core utils    │ auth.py, logging_config.py, pagination.py, etc.                          │
 ├───────────────┼──────────────────────────────────────────────────────────────────────────┤
 │ Alembic       │ Entire alembic/ folder                                                   │
 └───────────────┴──────────────────────────────────────────────────────────────────────────┘
 Phase 3: LLM Service (NEW)

 Create app/services/llm_service.py:
 - LLMService class with singleton pattern
 - analyze_text_report(text) - Qwen 3 for flood report parsing
 - analyze_flood_image(image_path) - Qwen 3-VL for depth estimation
 - is_available() - Health check with caching
 - get_health() - For API endpoint
 - Response caching and graceful degradation

 Phase 4: Agent Upgrades
 Agent: ScoutAgent
 Changes: Add llm_service in __init__, modify _process_and_forward_tweets() to use Qwen 3 for text + Qwen 3-VL for images, fallback to NLP if    
   unavailable
 ────────────────────────────────────────
 Agent: FloodAgent
 Changes: Add parse_text_advisory() and collect_and_parse_advisories() methods for PAGASA text bulletin parsing
 ────────────────────────────────────────
 Agent: HazardAgent
 Changes: Add Visual Confirmation Override in update_risk() - visual evidence with risk >0.8 overrides sensor data
 Phase 5: Main App & Data
 ┌────────────────────┬─────────────────────────────────────────────────────────────────────┐
 │        Task        │                               Action                                │
 ├────────────────────┼─────────────────────────────────────────────────────────────────────┤
 │ Main app           │ Copy main.py, add /api/llm/health endpoint, update startup logging  │
 ├────────────────────┼─────────────────────────────────────────────────────────────────────┤
 │ Data files         │ Copy data/marikina_graph.graphml, symlink app/data/timed_floodmaps/ │
 ├────────────────────┼─────────────────────────────────────────────────────────────────────┤
 │ Evacuation centers │ Copy app/data/evacuation_centers.csv                                │
 ├────────────────────┼─────────────────────────────────────────────────────────────────────┤
 │ Synthetic data     │ Copy app/data/synthetic/ and app/data/simulation_scenarios/         │
 └────────────────────┴─────────────────────────────────────────────────────────────────────┘
 Key New Features

 1. LLM Configuration (.env)

 OLLAMA_BASE_URL=http://localhost:11434
 LLM_TEXT_MODEL=qwen3
 LLM_VISION_MODEL=qwen3-vl
 LLM_TIMEOUT_SECONDS=30
 LLM_ENABLED=true

 2. Graceful Degradation

 LLM Available → Use Qwen 3/Qwen 3-VL
 LLM Unavailable → Fall back to existing spaCy NLP

 3. Visual Override Logic (HazardAgent)

 IF scout_report.visual_evidence == True
    AND scout_report.risk_score > 0.8
    AND scout_report.confidence > 0.8
 THEN
    Override official sensor data
    Mark affected edges as high-risk/impassable

 File Count Summary
 ┌────────────────┬───────────┬───────────────────────────┐
 │    Category    │   Count   │          Action           │
 ├────────────────┼───────────┼───────────────────────────┤
 │ Copy unchanged │ ~50 files │ Direct copy               │
 ├────────────────┼───────────┼───────────────────────────┤
 │ Refactor       │ 6 files   │ Copy + modify             │
 ├────────────────┼───────────┼───────────────────────────┤
 │ Create new     │ 2 files   │ llm_service.py, README.md │
 ├────────────────┼───────────┼───────────────────────────┤
 │ Data files     │ ~80 files │ Copy/symlink              │
 └────────────────┴───────────┴───────────────────────────┘
 Verification

 1. Unit test LLM service: pytest tests/unit/test_llm_service.py
 2. Start server: uvicorn app.main:app --reload
 3. Check health: GET /api/health and GET /api/llm/health
 4. Test routing: POST /api/route with sample coordinates
 5. Verify LLM fallback: Stop Ollama, confirm NLP fallback works

 Dependencies to Add

 # pyproject.toml
 dependencies = [
     # ... existing ...
     "ollama>=0.4.0",  # Qwen 3 LLM integration
 ]

 Critical Files to Modify

 1. app/services/llm_service.py - NEW (core LLM integration)
 2. app/agents/scout_agent.py - REFACTOR (Qwen 3 + VL integration)
 3. app/agents/hazard_agent.py - REFACTOR (Visual Override)
 4. app/agents/flood_agent.py - REFACTOR (advisory parsing)
 5. app/core/config.py - REFACTOR (LLM settings)
 6. config/agents.yaml - REFACTOR (llm_service section)