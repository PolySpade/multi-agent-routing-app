# MAS-FRO Backend v2

Multi-Agent System for Flood Route Optimization - Backend v2 with Qwen 3 LLM Integration

## Overview

MAS-FRO v2 enhances the original multi-agent flood routing system with Qwen 3 LLM capabilities for improved semantic understanding and multimodal flood detection.

### Key v2 Enhancements

- **Qwen 3 Text Analysis**: Enhanced flood report parsing with semantic understanding
- **Qwen 3-VL Vision**: Flood image analysis for depth estimation and risk assessment
- **Visual Override Logic**: High-confidence visual evidence can override official sensor data
- **Graceful Degradation**: Falls back to traditional NLP when LLM is unavailable

## Quick Start

### Prerequisites

- Python 3.10+
- [uv](https://github.com/astral-sh/uv) package manager
- [Ollama](https://ollama.ai/download) (for LLM features)

### Installation

```bash
# Clone and navigate to backend-v2
cd masfro-backend-v2

# Setup with uv
pip install uv -g
uv sync

# Activate virtual environment
# Windows:
.venv\Scripts\activate
# macOS/Linux:
source .venv/bin/activate

# Copy and configure environment
cp .env.example .env
# Edit .env with your API keys
```

### Ollama Setup (LLM Features)

```bash
# Install Ollama (https://ollama.ai/download)

# Pull required models
ollama pull qwen3
ollama pull qwen3-vl

# Verify Ollama is running
curl http://localhost:11434/api/tags
```

### Running the Server

```bash
# Development server
uvicorn app.main:app --reload

# Production server
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

### Verify Installation

```bash
# Health check
curl http://localhost:8000/api/health

# LLM health check
curl http://localhost:8000/api/llm/health
```

## Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              FASTAPI APPLICATION                             │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌───────────────┐  ┌───────────────┐  ┌───────────────┐                   │
│  │  FloodAgent   │  │  ScoutAgent   │  │ EvacManager   │                   │
│  │  + Qwen 3     │  │  + Qwen 3     │  │               │                   │
│  │  (Text Parse) │  │  + Qwen 3-VL  │  │               │                   │
│  └───────┬───────┘  └───────┬───────┘  └───────────────┘                   │
│          │                  │                                               │
│          └────────┬─────────┘                                               │
│                   ▼                                                         │
│           ┌───────────────┐                                                 │
│           │  LLM Service  │◄──────── Ollama API (localhost:11434)          │
│           │  (Centralized)│                                                 │
│           └───────────────┘                                                 │
│                   │                                                         │
│          ┌────────┴────────┐                                                │
│          ▼                 ▼                                                │
│    ┌───────────┐    ┌───────────┐                                           │
│    │  Qwen 3   │    │ Qwen 3-VL │                                           │
│    │  (Text)   │    │ (Vision)  │                                           │
│    └───────────┘    └───────────┘                                           │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

## New Features

### LLM Service (`app/services/llm_service.py`)

Centralized service for Qwen 3 integration:

```python
from app.services.llm_service import get_llm_service

llm = get_llm_service()

# Text analysis
result = llm.analyze_text_report("Baha sa J.P. Rizal, hanggang tuhod!")
# Returns: {'location': 'J.P. Rizal', 'severity': 0.5, 'is_flood_related': True, ...}

# Image analysis
result = llm.analyze_flood_image("/path/to/flood_image.jpg")
# Returns: {'estimated_depth_m': 0.3, 'risk_score': 0.6, ...}

# Advisory parsing
result = llm.parse_pagasa_advisory(advisory_text)
# Returns: {'warning_level': 'orange', 'affected_areas': [...], ...}
```

### Visual Override (HazardAgent)

When a scout report has:
- `visual_evidence == True`
- `risk_score > 0.8`
- `confidence > 0.8`

The visual evidence overrides official sensor data, enabling faster response to ground-truth conditions.

### Graceful Degradation

```
LLM Available → Use Qwen 3/Qwen 3-VL for analysis
LLM Unavailable → Fall back to existing spaCy NLP
```

## Configuration

### Environment Variables (`.env`)

```bash
# LLM Configuration
OLLAMA_BASE_URL=http://localhost:11434
LLM_TEXT_MODEL=qwen3
LLM_VISION_MODEL=qwen3-vl
LLM_TIMEOUT_SECONDS=30
LLM_ENABLED=true
```

### YAML Configuration (`config/agents.yaml`)

```yaml
llm_service:
  enable: true
  ollama:
    base_url: "http://localhost:11434"
    text_model: "qwen3"
    vision_model: "qwen3-vl"
  visual_override:
    enable: true
    min_risk_threshold: 0.8
    min_confidence_threshold: 0.8
```

## API Endpoints

### Health Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/health` | GET | System health check (includes LLM status) |
| `/api/llm/health` | GET | Detailed LLM service health |

### Routing Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/route` | POST | Calculate flood-safe route |
| `/api/evacuation/route` | POST | Calculate evacuation route |

## Testing

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=app

# Test LLM service specifically
pytest tests/unit/test_llm_service.py -v
```

## Disabling LLM

To run without LLM (fallback to NLP only):

```bash
# In .env
LLM_ENABLED=false

# Or via environment variable
export LLM_ENABLED=false
uvicorn app.main:app --reload
```

## Changes from v1

| Component | v1 | v2 |
|-----------|----|----|
| ScoutAgent text analysis | spaCy NLP | Qwen 3 (fallback: NLP) |
| ScoutAgent image analysis | N/A | Qwen 3-VL |
| FloodAgent advisory parsing | Rule-based | Qwen 3 (fallback: rules) |
| HazardAgent Visual Override | N/A | Enabled |
| LLM health endpoint | N/A | `/api/llm/health` |

## License

MIT License - See LICENSE file for details.

## Authors

MAS-FRO Development Team - February 2026
