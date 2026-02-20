# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Structure

This is a multi-agent routing application built with a microservices architecture:

- **masfro-backend/**: FastAPI backend server handling routing algorithms and multi-agent simulation
- **masfro-frontend/**: Next.js frontend application for the user interface

### Backend Architecture (masfro-backend/)

The backend is a FastAPI application focused on routing optimization using multi-agent systems:

- **app/main.py**: Main FastAPI application entry point with route endpoints
- **app/agents/**: Multi-agent system components:
  - `routing_agent.py`: Core routing algorithm implementation
  - `scout_agent.py`: Path exploration and reconnaissance
  - `flood_agent.py`: Weather condition monitoring
  - `hazard_agent.py`: Risk assessment
  - `base_agent.py`: Base agent class for common functionality
- **app/environment/**: Graph management and environment simulation
- **app/core/**: Core utilities and shared components
- **app/services/**: External service integrations
- **app/data/**: Data models and storage

Key dependencies include OSMnx for map data, NetworkX for graph operations, and Selenium for web scraping.

### Frontend Architecture (masfro-frontend/)

Next.js application using App Router with mapping capabilities:

- **src/app/**: Next.js App Router pages and layouts
- **src/components/**: Reusable React components
- **src/utils/**: Utility functions

Mapping libraries include Leaflet, React-Leaflet, and Mapbox GL for interactive maps.

## Development Commands

### Backend (masfro-backend/)

```bash
# Setup (requires uv package manager)
pip install uv -g
uv sync
.venv\Scripts\activate  # Windows
source .venv/bin/activate  # macOS/Linux

# Run development server
uvicorn app.main:app --reload
```

### Frontend (masfro-frontend/)

```bash
# Install dependencies
npm install

# Development server
npm run dev

# Build for production
npm run build

# Start production server
npm start

# Lint code
npm run lint
```

## Key Concepts

The application implements a multi-agent routing system where different agents collaborate to find optimal routes considering various factors like weather conditions, hazards, and real-time data. The DynamicGraphEnvironment manages the road network graph using OSMnx and NetworkX for route optimization.

The frontend provides an interactive map interface for route visualization and user interaction, while the backend handles the complex multi-agent routing computations.

## Agent Utilization
