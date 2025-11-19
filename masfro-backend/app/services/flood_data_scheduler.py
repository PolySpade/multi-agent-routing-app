# filename: app/services/flood_data_scheduler.py

"""
Flood Data Collection Scheduler
================================

This module provides an async background scheduler for automatic flood data
collection from FloodAgent at regular intervals.

Author: MAS-FRO Development Team
Date: November 2025
"""

import asyncio
import logging
from datetime import datetime
from typing import Optional, Dict, Any

from app.database import SessionLocal, FloodDataRepository

logger = logging.getLogger(__name__)


class FloodDataScheduler:
    """
    Background scheduler for automatic flood data collection.

    Runs FloodAgent data collection at configured intervals and provides
    statistics about collection runs.

    Attributes:
        flood_agent: Reference to FloodAgent instance
        interval_seconds: Collection interval in seconds
        is_running: Whether scheduler is currently running
        task: Background asyncio task
        stats: Collection statistics
    """

    def __init__(
        self,
        flood_agent,
        interval_seconds: int = 300,
        ws_manager: Optional[Any] = None,
        hazard_agent: Optional[Any] = None
    ):
        """
        Initialize the scheduler.

        Args:
            flood_agent: FloodAgent instance to schedule
            interval_seconds: Collection interval (default: 300 = 5 minutes)
            ws_manager: WebSocket ConnectionManager for broadcasting updates
            hazard_agent: HazardAgent instance to forward data to (optional)
        """
        self.flood_agent = flood_agent
        self.interval_seconds = interval_seconds
        self.ws_manager = ws_manager
        self.hazard_agent = hazard_agent
        self.is_running = False
        self.task: Optional[asyncio.Task] = None

        # Statistics
        self.stats = {
            "total_runs": 0,
            "successful_runs": 0,
            "failed_runs": 0,
            "last_run_time": None,
            "last_success_time": None,
            "last_error": None,
            "scheduler_start_time": None,
            "data_points_collected": 0
        }

        logger.info(
            f"FloodDataScheduler initialized with interval={interval_seconds}s "
            f"({interval_seconds/60:.1f} minutes), "
            f"WebSocket broadcasting={'enabled' if ws_manager else 'disabled'}, "
            f"HazardAgent forwarding={'enabled' if hazard_agent else 'disabled'}"
        )

    def _save_to_database(
        self,
        data: Dict[str, Any],
        duration_seconds: float,
        data_source: str = "real"
    ) -> Optional[Any]:
        """
        Save collected flood data to database.

        Args:
            data: Flood data dictionary from FloodAgent (flat structure)
            duration_seconds: Collection duration
            data_source: Data source ('real' or 'simulated')

        Returns:
            FloodDataCollection instance or None on error
        """
        db = SessionLocal()
        try:
            repo = FloodDataRepository(db)

            # Extract river levels from flat dictionary
            # FloodAgent returns: {"Montalban": {...}, "Nangka": {...}, "Marikina_weather": {...}}
            river_levels_data = []
            weather_data_dict = None

            for key, value in data.items():
                if isinstance(value, dict):
                    # Check if this is weather data (keys ending with _weather)
                    if key.endswith("_weather"):
                        # Extract weather data
                        weather_data_dict = {
                            "rainfall_1h": value.get("rainfall_1h"),
                            "rainfall_3h": value.get("rainfall_3h"),
                            "rainfall_24h_forecast": value.get("rainfall_24h_forecast"),
                            "intensity": value.get("intensity"),
                            "intensity_category": value.get("intensity_category"),
                            "temperature": value.get("temperature"),
                            "humidity": value.get("humidity"),
                            "pressure": value.get("pressure"),
                            "weather_main": value.get("weather_main"),
                            "weather_description": value.get("weather_description"),
                            "wind_speed": value.get("wind_speed"),
                            "wind_direction": value.get("wind_direction"),
                            "data_source": value.get("source", "OpenWeatherMap"),
                        }
                    else:
                        # This is a river station
                        river_levels_data.append({
                            "station_name": key,
                            "water_level": value.get("water_level", 0.0),
                            "risk_level": value.get("risk_level", "NORMAL"),
                            "alert_level": value.get("alert_level"),
                            "alarm_level": value.get("alarm_level"),
                            "critical_level": value.get("critical_level"),
                            "data_source": value.get("source", "PAGASA"),
                        })

            # Save to database
            collection = repo.create_collection(
                river_levels_data=river_levels_data,
                weather_data_dict=weather_data_dict,
                data_source=data_source,
                duration_seconds=duration_seconds,
            )

            logger.info(f"[DB] Data saved to database: collection_id={collection.id}")
            return collection

        except Exception as e:
            logger.error(f"[ERROR] Database save error: {e}")
            return None
        finally:
            db.close()

    def _save_failed_collection(self, error_message: str, data_source: str = "real"):
        """
        Save a failed collection record to database.

        Args:
            error_message: Error description
            data_source: Data source that failed
        """
        db = SessionLocal()
        try:
            repo = FloodDataRepository(db)
            collection = repo.create_failed_collection(
                error_message=error_message,
                data_source=data_source,
            )
            logger.info(f"[DB] Failed collection saved: collection_id={collection.id}")
        except Exception as e:
            logger.error(f"[ERROR] Failed to save error record: {e}")
        finally:
            db.close()

    async def _collection_loop(self):
        """
        Background loop that runs data collection at intervals.

        This is the main scheduler loop that runs in the background.
        """
        logger.info("FloodDataScheduler started")
        self.stats["scheduler_start_time"] = datetime.now()

        while self.is_running:
            try:
                # Run data collection
                logger.info("Scheduler triggering flood data collection...")
                start_time = datetime.now()

                # Call FloodAgent data collection (synchronous call in async context)
                data = await asyncio.to_thread(
                    self.flood_agent.collect_and_forward_data
                )

                end_time = datetime.now()
                duration = (end_time - start_time).total_seconds()

                # Update statistics
                self.stats["total_runs"] += 1
                self.stats["last_run_time"] = end_time

                if data:
                    self.stats["successful_runs"] += 1
                    self.stats["last_success_time"] = end_time
                    self.stats["data_points_collected"] += len(data)

                    logger.info(
                        f"[OK] Scheduled collection successful: {len(data)} data points "
                        f"in {duration:.2f}s"
                    )

                    # Save to database
                    await asyncio.to_thread(
                        self._save_to_database,
                        data,
                        duration
                    )

                    # Broadcast flood data update via WebSocket
                    if self.ws_manager:
                        try:
                            await self.ws_manager.broadcast_flood_update(data)
                            await self.ws_manager.check_and_alert_critical_levels(data)
                            logger.debug("WebSocket broadcast completed")
                        except Exception as ws_error:
                            logger.error(f"WebSocket broadcast error: {ws_error}")

                    # Forward to HazardAgent cache for frontend API endpoints
                    if self.hazard_agent:
                        try:
                            await asyncio.to_thread(
                                self.hazard_agent.update_risk,
                                flood_data=data,
                                scout_data=[],
                                time_step=0  # Real-time collection, not simulation
                            )
                            logger.info(
                                f"✓ Forwarded {len(data)} data points to HazardAgent cache"
                            )
                        except Exception as hazard_error:
                            logger.error(f"HazardAgent forwarding error: {hazard_error}")

                else:
                    self.stats["failed_runs"] += 1
                    logger.warning("[WARN] Scheduled collection returned no data")
                    # Save failed collection
                    await asyncio.to_thread(
                        self._save_failed_collection,
                        "Collection returned no data"
                    )

            except Exception as e:
                self.stats["failed_runs"] += 1
                self.stats["last_error"] = str(e)
                self.stats["last_run_time"] = datetime.now()
                logger.error(f"[ERROR] Scheduled collection error: {e}")
                # Save failed collection
                await asyncio.to_thread(
                    self._save_failed_collection,
                    str(e)
                )

            # Wait for next interval
            if self.is_running:
                logger.debug(f"Next collection in {self.interval_seconds}s...")
                await asyncio.sleep(self.interval_seconds)

        logger.info("FloodDataScheduler stopped")

    async def start(self):
        """
        Start the background scheduler.

        Creates and runs the background task for automatic data collection.
        """
        if self.is_running:
            logger.warning("Scheduler already running")
            return

        self.is_running = True
        self.task = asyncio.create_task(self._collection_loop())
        logger.info(
            f"[OK] FloodDataScheduler started (interval={self.interval_seconds}s)"
        )

    async def stop(self):
        """
        Stop the background scheduler.

        Gracefully stops the scheduler and waits for the current collection
        to complete.
        """
        if not self.is_running:
            logger.warning("Scheduler not running")
            return

        logger.info("Stopping FloodDataScheduler...")
        self.is_running = False

        if self.task:
            # Wait for current collection to complete (with timeout)
            try:
                await asyncio.wait_for(self.task, timeout=30.0)
            except asyncio.TimeoutError:
                logger.warning("Scheduler stop timed out, cancelling task")
                self.task.cancel()

        logger.info("[OK] FloodDataScheduler stopped")

    def get_status(self) -> Dict[str, Any]:
        """
        Get current scheduler status and statistics.

        Returns:
            Dict with scheduler status and statistics
        """
        uptime = None
        if self.stats["scheduler_start_time"]:
            uptime = (datetime.now() - self.stats["scheduler_start_time"]).total_seconds()

        success_rate = 0.0
        if self.stats["total_runs"] > 0:
            success_rate = (self.stats["successful_runs"] / self.stats["total_runs"]) * 100

        return {
            "is_running": self.is_running,
            "interval_seconds": self.interval_seconds,
            "interval_minutes": self.interval_seconds / 60,
            "uptime_seconds": uptime,
            "statistics": {
                "total_runs": self.stats["total_runs"],
                "successful_runs": self.stats["successful_runs"],
                "failed_runs": self.stats["failed_runs"],
                "success_rate_percent": round(success_rate, 2),
                "data_points_collected": self.stats["data_points_collected"],
                "last_run_time": self.stats["last_run_time"].isoformat() if self.stats["last_run_time"] else None,
                "last_success_time": self.stats["last_success_time"].isoformat() if self.stats["last_success_time"] else None,
                "last_error": self.stats["last_error"]
            }
        }

    async def trigger_manual_collection(self) -> Dict[str, Any]:
        """
        Manually trigger a data collection (outside of schedule).

        Returns:
            Dict with collection results
        """
        logger.info("Manual collection triggered via API")

        try:
            start_time = datetime.now()
            data = await asyncio.to_thread(
                self.flood_agent.collect_and_forward_data
            )
            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()

            # Save to database
            if data:
                await asyncio.to_thread(
                    self._save_to_database,
                    data,
                    duration
                )

            # Broadcast flood data update via WebSocket
            if data and self.ws_manager:
                try:
                    await self.ws_manager.broadcast_flood_update(data)
                    await self.ws_manager.check_and_alert_critical_levels(data)
                    logger.info("Manual collection broadcast completed")
                except Exception as ws_error:
                    logger.error(f"WebSocket broadcast error: {ws_error}")

            # Forward to HazardAgent cache for frontend API endpoints
            if data and self.hazard_agent:
                try:
                    await asyncio.to_thread(
                        self.hazard_agent.update_risk,
                        flood_data=data,
                        scout_data=[],
                        time_step=0  # Manual collection, not simulation
                    )
                    logger.info(
                        f"✓ Forwarded {len(data)} data points to HazardAgent cache (manual)"
                    )
                except Exception as hazard_error:
                    logger.error(f"HazardAgent forwarding error: {hazard_error}")

            return {
                "status": "success",
                "data_points": len(data) if data else 0,
                "duration_seconds": round(duration, 2),
                "timestamp": end_time.isoformat(),
                "broadcasted": bool(data and self.ws_manager),
                "saved_to_db": bool(data)
            }

        except Exception as e:
            logger.error(f"Manual collection error: {e}")
            # Save failed collection
            await asyncio.to_thread(
                self._save_failed_collection,
                str(e)
            )
            return {
                "status": "error",
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }


# Global scheduler instance (will be initialized in main.py)
scheduler: Optional[FloodDataScheduler] = None


def get_scheduler() -> Optional[FloodDataScheduler]:
    """Get the global scheduler instance."""
    return scheduler


def set_scheduler(new_scheduler: FloodDataScheduler):
    """Set the global scheduler instance."""
    global scheduler
    scheduler = new_scheduler
