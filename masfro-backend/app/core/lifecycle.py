"""
Application lifecycle event handlers.

Manages startup and shutdown tasks for the MAS-FRO application.
"""

import logging
from pathlib import Path
from fastapi import FastAPI
from app.core.logging_config import setup_logging
from app.database import check_connection, init_db
from app.services.flood_data_scheduler import get_scheduler
from app.core.state import get_app_state

logger = logging.getLogger(__name__)


def register_lifecycle_events(app: FastAPI):
    """
    Register startup and shutdown events for the application.

    Args:
        app: FastAPI application instance
    """

    @app.on_event("startup")
    async def startup_event():
        """Start background tasks on application startup."""
        # Initialize logging system (ensure logs directory exists)
        setup_logging()
        logger.info("="*60)
        logger.info("MAS-FRO Backend Starting Up")
        logger.info("="*60)
        logger.info("Structured logging initialized - logs written to logs/masfro.log")

        # Check database connection
        logger.info("Checking database connection...")
        if check_connection():
            logger.info("Database connection successful")
            # Initialize database tables (if not exist)
            init_db()
        else:
            logger.error("Database connection failed - historical data storage disabled")

        # Load initial flood data to populate risk scores
        logger.info("Loading initial flood risk data...")
        state = get_app_state()
        try:
            # Load default GeoTIFF data (light scenario, time step 1)
            geotiff_path = Path(__file__).parent.parent / "data" / "geotiff_data" / "rr01" / "rr01_step_01.tif"

            if geotiff_path.exists() and state.hazard_agent and state.environment:
                logger.info(f"Loading initial risk data from {geotiff_path}")

                # Process GeoTIFF to get flood data
                import rasterio
                with rasterio.open(geotiff_path) as src:
                    flood_array = src.read(1)
                    transform = src.transform

                # Convert to edge risk scores (simplified version)
                edge_updates = {}
                for u, v, key, data in state.environment.graph.edges(keys=True, data=True):
                    # Get edge midpoint coordinates
                    u_coords = state.environment.graph.nodes[u]
                    v_coords = state.environment.graph.nodes[v]
                    mid_lat = (u_coords['y'] + v_coords['y']) / 2
                    mid_lon = (u_coords['x'] + v_coords['x']) / 2

                    # Sample flood depth at edge location
                    row, col = ~transform * (mid_lon, mid_lat)
                    row, col = int(row), int(col)

                    if 0 <= row < flood_array.shape[0] and 0 <= col < flood_array.shape[1]:
                        flood_depth = float(flood_array[row, col])
                        # Convert depth to risk score (0-1)
                        if flood_depth < 0.1:
                            risk_score = 0.0
                        elif flood_depth < 0.5:
                            risk_score = 0.3
                        elif flood_depth < 1.0:
                            risk_score = 0.6
                        elif flood_depth < 2.0:
                            risk_score = 0.8
                        else:
                            risk_score = 0.95  # Near impassable

                        edge_updates[(u, v, key)] = risk_score

                # Apply updates to graph
                state.environment.update_edge_risks(edge_updates)
                logger.info(f"Initial flood data loaded: Updated {len(edge_updates)} edges with risk scores")

                # Log sample of high-risk edges
                high_risk_count = sum(1 for risk in edge_updates.values() if risk >= 0.7)
                logger.info(f"High-risk edges (>= 70%): {high_risk_count}")

            else:
                logger.warning(f"GeoTIFF data not found at {geotiff_path} - graph will start with zero risk")

        except Exception as e:
            logger.error(f"Failed to load initial flood data: {e}")
            logger.warning("Continuing with zero risk scores - all roads passable")

        # Start scheduler
        logger.info("Starting background scheduler...")
        scheduler = get_scheduler()
        if scheduler:
            await scheduler.start()
            logger.info("Automated flood data collection started (every 5 minutes)")
        else:
            logger.warning("Scheduler not initialized")

    @app.on_event("shutdown")
    async def shutdown_event():
        """Stop background tasks on application shutdown."""
        logger.info("="*60)
        logger.info("MAS-FRO Backend Shutting Down")
        logger.info("="*60)
        logger.info("Stopping background scheduler...")
        scheduler = get_scheduler()
        if scheduler:
            await scheduler.stop()
            logger.info("Scheduler stopped gracefully")
        logger.info("MAS-FRO backend shutdown complete")
