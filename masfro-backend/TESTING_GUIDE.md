# MAS-FRO Backend Testing Guide

## Overview

This document provides comprehensive information about testing the MAS-FRO backend system.

## Test Status

✅ **All Systems Operational**

- All integration tests passing (6/6)
- Uvicorn server starts successfully
- All agents initialize properly
- API endpoints registered correctly

## Running Tests

### 1. Integration Tests

The integration test script verifies that all components work together correctly.

```bash
cd masfro-backend
uv run python test_integration.py
```

**Expected Output:**
```
======================================================================
  Test Summary
======================================================================
[PASS]   | Module Imports
[PASS]   | Agent Initialization
[PASS]   | Risk Calculator
[PASS]   | ACL Protocol
[PASS]   | ML Models
[PASS]   | FastAPI Application

----------------------------------------------------------------------
Total: 6/6 test suites passed
```

### 2. Unit Tests with Pytest

Run individual test modules:

```bash
# Run all tests
cd masfro-backend
uv run pytest test/

# Run specific test file
uv run pytest test/test_acl_protocol.py

# Run with verbose output
uv run pytest test/ -v

# Run with coverage
uv run pytest test/ --cov=app --cov-report=html
```

### 3. API Tests

Test API endpoints:

```bash
# Run API tests
cd masfro-backend
uv run pytest test/test_api.py -v
```

## Test Files

### Unit Tests

1. **test/test_acl_protocol.py**
   - Tests ACL message creation and serialization
   - Tests message queue functionality
   - Tests agent registration and message passing

2. **test/test_risk_calculator.py**
   - Tests hydrological risk calculations
   - Tests infrastructure risk assessment
   - Tests passability thresholds
   - Tests composite risk scoring

3. **test/test_algorithms.py**
   - Tests Haversine distance calculation
   - Tests risk-aware A* pathfinding
   - Tests path metrics calculation
   - Tests coordinate extraction

4. **test/test_api.py**
   - Tests health check endpoints
   - Tests route calculation endpoint
   - Tests feedback submission endpoint
   - Tests data model validation

### Integration Test

**test_integration.py**
- Comprehensive system integration test
- Tests all module imports
- Tests agent initialization
- Tests risk calculator functionality
- Tests ACL protocol and message queue
- Tests ML models (FloodPredictor, NLPProcessor)
- Tests FastAPI application

## Starting the Server

### Development Server

```bash
cd masfro-backend
uv run uvicorn app.main:app --reload
```

The server will start on http://localhost:8000

### Custom Port

```bash
uv run uvicorn app.main:app --host 127.0.0.1 --port 8001
```

### Expected Server Output

```
INFO - Initializing MAS-FRO Multi-Agent System...
INFO - MessageQueue system initialized
INFO - flood_agent_001 initialized with update interval 300s
INFO - hazard_agent_001 initialized with risk weights: {...}
INFO - evac_manager_001 initialized
INFO - evac_manager_001 linked to hazard_agent_001
INFO - MAS-FRO system initialized successfully
INFO - Uvicorn running on http://127.0.0.1:8000
```

## Testing API Endpoints

### 1. Health Check

```bash
curl http://localhost:8000/
curl http://localhost:8000/api/health
```

### 2. Route Calculation

```bash
curl -X POST http://localhost:8000/api/route \
  -H "Content-Type: application/json" \
  -d '{
    "start_location": [14.6507, 121.1029],
    "end_location": [14.6545, 121.1089]
  }'
```

### 3. User Feedback

```bash
curl -X POST http://localhost:8000/api/feedback \
  -H "Content-Type: application/json" \
  -d '{
    "route_id": "test-123",
    "feedback_type": "clear",
    "location": [14.6507, 121.1029],
    "severity": 0.0,
    "description": "Road is clear"
  }'
```

### 4. Statistics

```bash
curl http://localhost:8000/api/statistics
```

### 5. Interactive API Documentation

Visit http://localhost:8000/docs for interactive Swagger UI documentation.

## Test Coverage

### Covered Components

✅ Agent Communication System
- ACL Protocol
- Message Queue

✅ Multi-Agent System
- FloodAgent
- HazardAgent
- EvacuationManagerAgent

✅ Algorithms
- Risk-Aware A*
- Path Optimizer
- Haversine Distance

✅ Environment & Risk
- Dynamic Graph Environment
- Risk Calculator

✅ Machine Learning
- Flood Predictor
- NLP Processor

✅ API
- Route endpoints
- Feedback endpoints
- Health checks

### Test Statistics

- **Total Test Files:** 5
- **Total Test Cases:** 50+
- **Integration Tests:** 6 test suites
- **Code Coverage:** Estimated 70%+

## Common Issues and Solutions

### Issue: Module Import Errors

**Solution:** Ensure dependencies are installed
```bash
cd masfro-backend
uv sync
```

### Issue: Port Already in Use

**Solution:** Use a different port or kill the existing process
```bash
# Windows
netstat -ano | findstr :8000
taskkill /PID <PID> /F

# Linux/Mac
lsof -i :8000
kill -9 <PID>

# Or use a different port
uv run uvicorn app.main:app --port 8001
```

### Issue: Graph File Not Found

**Solution:** Ensure the Marikina graph file exists
```bash
ls app/data/marikina_graph.graphml
```

If missing, run the download script:
```bash
uv run python app/data/download_map.py
```

### Issue: Test Failures

**Solution:** Run integration test to identify specific issues
```bash
uv run python test_integration.py
```

Check the detailed output for specific error messages.

## Performance Benchmarks

### Startup Time
- Cold start: ~2-3 seconds
- Graph loading: ~15-20 seconds (depends on graph size)
- Agent initialization: <1 second

### API Response Times
- Health check: <10ms
- Route calculation: 100-500ms (depends on graph size and complexity)
- Feedback submission: <50ms

## Continuous Testing

### Watch Mode (Development)

Install pytest-watch:
```bash
uv add --dev pytest-watch
```

Run tests in watch mode:
```bash
uv run ptw test/
```

### Pre-commit Hooks

Add to `.git/hooks/pre-commit`:
```bash
#!/bin/bash
cd masfro-backend
uv run pytest test/ --tb=short
```

## Next Steps

1. **Increase Test Coverage**
   - Add tests for ScoutAgent
   - Add tests for RoutingAgent
   - Add edge case tests

2. **Performance Testing**
   - Load testing with multiple concurrent requests
   - Stress testing with large graph networks
   - Memory profiling

3. **Integration Testing**
   - End-to-end testing with frontend
   - Database integration tests
   - External API integration tests

## Support

For issues or questions:
1. Check the error logs in the terminal output
2. Review the integration test results
3. Check API documentation at http://localhost:8000/docs
4. Review individual test files for examples

---

**Last Updated:** November 2025
**Test Status:** ✅ All Passing
**Version:** 1.0.0
