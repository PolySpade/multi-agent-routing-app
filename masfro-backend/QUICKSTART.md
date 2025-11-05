# MAS-FRO Backend Quick Start Guide

## 🚀 Get Started in 5 Minutes

### Prerequisites

- Python 3.10 or higher
- UV package manager ([Install UV](https://github.com/astral-sh/uv))

### Step 1: Install Dependencies

```bash
cd masfro-backend
uv sync
```

This will install all required dependencies including:
- FastAPI
- NetworkX
- OSMnx
- scikit-learn
- Selenium
- And more...

### Step 2: Verify Installation

Run the integration test to ensure everything is set up correctly:

```bash
uv run python test_integration.py
```

**Expected output:**
```
Total: 6/6 test suites passed
```

### Step 3: Start the Server

```bash
uv run uvicorn app.main:app --reload
```

**Server will start at:** http://localhost:8000

### Step 4: Test the API

Open your browser and visit:
- **Interactive Docs:** http://localhost:8000/docs
- **Health Check:** http://localhost:8000/api/health

Or use curl:
```bash
# Health check
curl http://localhost:8000/api/health

# Calculate a route
curl -X POST http://localhost:8000/api/route \
  -H "Content-Type: application/json" \
  -d '{
    "start_location": [14.6507, 121.1029],
    "end_location": [14.6545, 121.1089]
  }'
```

## 📋 Available Commands

### Development

```bash
# Start development server with auto-reload
uv run uvicorn app.main:app --reload

# Start on custom port
uv run uvicorn app.main:app --port 8001

# Start with specific host
uv run uvicorn app.main:app --host 0.0.0.0 --port 8000
```

### Testing

```bash
# Run integration tests
uv run python test_integration.py

# Run unit tests
uv run pytest test/

# Run with coverage
uv run pytest test/ --cov=app --cov-report=html

# Run specific test file
uv run pytest test/test_api.py -v
```

### Code Quality

```bash
# Format code
uv run ruff format .

# Check linting
uv run ruff check .

# Fix linting issues
uv run ruff check --fix .
```

## 🔧 Configuration

### Environment Variables

Create a `.env` file in the `masfro-backend/` directory:

```env
# API Configuration
API_HOST=0.0.0.0
API_PORT=8000

# Logging
LOG_LEVEL=INFO

# Data Sources (Optional - for production)
PAGASA_API_URL=https://api.pagasa.dost.gov.ph/...
NOAH_API_URL=https://api.noah.dost.gov.ph/...
```

## 📊 System Status

After starting the server, you can check system status:

```bash
curl http://localhost:8000/api/health
```

**Response:**
```json
{
  "status": "healthy",
  "graph_status": "loaded",
  "agents": {
    "flood_agent": "active",
    "hazard_agent": "active",
    "evacuation_manager": "active"
  }
}
```

## 🗺️ Map Data

The system uses OSMnx to load the Marikina City road network. The graph is automatically loaded on startup from:

```
app/data/marikina_graph.graphml
```

If you need to regenerate the map:

```bash
uv run python app/data/download_map.py
```

## 📡 API Endpoints

### Route Calculation

**POST** `/api/route`

```json
{
  "start_location": [14.6507, 121.1029],
  "end_location": [14.6545, 121.1089],
  "preferences": {
    "avoid_floods": true
  }
}
```

### User Feedback

**POST** `/api/feedback`

```json
{
  "route_id": "route-123",
  "feedback_type": "clear",
  "location": [14.6507, 121.1029],
  "severity": 0.0,
  "description": "Road is clear"
}
```

### System Statistics

**GET** `/api/statistics`

Returns:
- Total routes calculated
- User feedback statistics
- Graph network statistics

## 🐛 Troubleshooting

### Server won't start

1. Check if port is already in use:
   ```bash
   # Windows
   netstat -ano | findstr :8000

   # Linux/Mac
   lsof -i :8000
   ```

2. Use a different port:
   ```bash
   uv run uvicorn app.main:app --port 8001
   ```

### Import errors

Make sure dependencies are installed:
```bash
uv sync
```

### Graph file missing

Download the Marikina map:
```bash
uv run python app/data/download_map.py
```

## 📚 Documentation

- **API Documentation:** http://localhost:8000/docs
- **Testing Guide:** [TESTING_GUIDE.md](TESTING_GUIDE.md)
- **Implementation Summary:** [IMPLEMENTATION_SUMMARY.md](IMPLEMENTATION_SUMMARY.md)
- **Code Documentation:** [CLAUDE.md](CLAUDE.md)

## 🎯 Next Steps

1. **Explore the API**
   - Visit http://localhost:8000/docs
   - Try different route requests
   - Submit test feedback

2. **Run Tests**
   - Execute integration tests
   - Check test coverage
   - Add custom tests

3. **Customize**
   - Adjust risk weights in `HazardAgent`
   - Configure data update intervals in `FloodAgent`
   - Modify routing preferences

4. **Integrate Frontend**
   - Connect Next.js frontend
   - Implement map visualization
   - Add user interface

## 📞 Support

For issues or questions:
1. Check [TESTING_GUIDE.md](TESTING_GUIDE.md)
2. Review server logs
3. Run integration tests
4. Check API documentation

## 🎉 You're Ready!

Your MAS-FRO backend is now running and ready to calculate flood-safe routes!

---

**Quick Links:**
- 📖 API Docs: http://localhost:8000/docs
- 🏥 Health Check: http://localhost:8000/api/health
- 📊 Statistics: http://localhost:8000/api/statistics

**Version:** 1.0.0
**Last Updated:** November 2025
