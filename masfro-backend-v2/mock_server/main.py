"""
Mock Data Server for MAS-FRO Simulation Testing.

A standalone FastAPI application that serves data in the exact same formats
as real external sites (PAGASA, OpenWeatherMap, Google News RSS, social media).
The existing scrapers hit it with zero logic changes - only base URLs are swapped.

Usage:
    python -m mock_server.run
    # or
    uvicorn mock_server.main:app --host 0.0.0.0 --port 8081
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .routers import pagasa_router, weather_router, news_router, social_router, admin_router
from .scenarios import load_scenario

app = FastAPI(
    title="MAS-FRO Mock Data Server",
    description="Serves mock data matching real external site formats for simulation testing",
    version="1.0.0",
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(pagasa_router.router)
app.include_router(weather_router.router)
app.include_router(news_router.router)
app.include_router(social_router.router)
app.include_router(admin_router.router)


@app.get("/")
async def root():
    return {
        "service": "MAS-FRO Mock Data Server",
        "version": "1.0.0",
        "endpoints": {
            "pagasa_river": "/pagasa/water/map.do",
            "pagasa_dam": "/pagasa/flood",
            "pagasa_advisory": "/pagasa/advisory/{id}",
            "weather_current": "/weather/data/2.5/weather",
            "weather_forecast": "/weather/data/2.5/forecast",
            "news_rss": "/news/rss",
            "social_feed": "/social/feed",
            "social_api": "/social/api/tweets",
            "admin": "/admin",
            "admin_scenario": "/admin/scenario/load",
        }
    }


@app.on_event("startup")
async def startup():
    """Load the configured scenario on startup (defaults to 'light')."""
    import mock_server
    scenario = getattr(mock_server, "_initial_scenario", "light")
    result = load_scenario(scenario)
    import logging
    logging.getLogger("mock_server").info(f"Loaded {scenario} scenario: {result}")
