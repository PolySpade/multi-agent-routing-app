"""
WebSocket Connection Manager for real-time flood updates.

Manages WebSocket connections and broadcasts flood data, alerts, and system updates.
"""

import json
import logging
import threading
from typing import Set, Dict, Any, Optional
from datetime import datetime
from decimal import Decimal
from fastapi import WebSocket
from starlette.websockets import WebSocketDisconnect

logger = logging.getLogger(__name__)


class DateTimeEncoder(json.JSONEncoder):
    """
    Custom JSON encoder that handles datetime and Decimal objects.

    Converts datetime objects to ISO format strings for JSON serialization.
    """
    def default(self, obj):
        if isinstance(obj, datetime):
            return obj.isoformat()
        elif isinstance(obj, Decimal):
            return float(obj)
        return super().default(obj)


def to_json_serializable(data: Any) -> str:
    """
    Convert data to JSON string with datetime handling.

    Args:
        data: Data to convert (dict, list, or primitive)

    Returns:
        JSON string with all datetime objects converted
    """
    return json.dumps(data, cls=DateTimeEncoder)


def convert_datetimes_to_strings(obj: Any) -> Any:
    """
    Recursively convert all datetime objects to ISO format strings.

    Args:
        obj: Object to convert (can be dict, list, datetime, or primitive)

    Returns:
        Converted object with all datetime instances as ISO strings
    """
    if isinstance(obj, datetime):
        return obj.isoformat()
    elif isinstance(obj, dict):
        return {key: convert_datetimes_to_strings(value) for key, value in obj.items()}
    elif isinstance(obj, list):
        return [convert_datetimes_to_strings(item) for item in obj]
    elif isinstance(obj, tuple):
        return tuple(convert_datetimes_to_strings(item) for item in obj)
    else:
        return obj


class ConnectionManager:
    """
    Manages WebSocket connections for real-time flood updates.

    Broadcasts:
    - Flood data updates (every 5 minutes from scheduler)
    - Critical water level alerts (Alarm/Critical thresholds)
    - Scheduler status updates
    - System notifications
    """

    def __init__(self):
        """Initialize connection manager."""
        self.active_connections: Set[WebSocket] = set()
        self._lock = threading.Lock()  # Thread safety for connection set
        self.last_flood_state: Optional[Dict[str, Any]] = None
        self.critical_stations: Set[str] = set()  # Track critical river stations

    async def connect(self, websocket: WebSocket):
        """Accept new WebSocket connection."""
        await websocket.accept()
        with self._lock:
            self.active_connections.add(websocket)
            count = len(self.active_connections)
        logger.info(
            f"WebSocket connected. Total connections: {count}"
        )

    def disconnect(self, websocket: WebSocket):
        """Remove WebSocket connection."""
        with self._lock:
            self.active_connections.discard(websocket)
            count = len(self.active_connections)
        logger.info(
            f"WebSocket disconnected. "
            f"Total connections: {count}"
        )

    async def broadcast(self, message: dict):
        """
        Broadcast message to all connected clients.

        Uses custom JSON encoder to handle datetime objects.
        """
        disconnected = set()

        # Serialize message with custom encoder for datetime handling
        try:
            json_str = to_json_serializable(message)
            logger.debug(f"Successfully serialized message of type: {message.get('type')}")
        except Exception as e:
            logger.error(f"JSON serialization error: {e}")
            logger.error(f"Message keys: {message.keys()}")
            logger.error(f"Message type field: {message.get('type')}")
            # Try to identify which field has the datetime issue
            for key, value in message.items():
                try:
                    json.dumps({key: value}, cls=DateTimeEncoder)
                except Exception as field_error:
                    logger.error(f"Field '{key}' caused error: {field_error}, value type: {type(value)}")
            raise  # Re-raise to prevent sending bad data

        # Create a copy of connections to avoid modification during iteration
        with self._lock:
            connections_copy = list(self.active_connections)

        for connection in connections_copy:
            try:
                # Check if connection is still in active set (might be removed by another thread)
                with self._lock:
                    if connection not in self.active_connections:
                        continue

                await connection.send_text(json_str)
                logger.debug("send_text successful")
            except WebSocketDisconnect:
                logger.info(f"WebSocket disconnected during broadcast")
                disconnected.add(connection)
            except Exception as e:
                # Handle any connection errors gracefully
                logger.warning(f"Failed to send to WebSocket: {type(e).__name__}: {e}")
                disconnected.add(connection)

        # Clean up disconnected clients
        for conn in disconnected:
            self.disconnect(conn)

    async def send_personal_message(self, message: dict, websocket: WebSocket):
        """Send message to specific client."""
        try:
            await websocket.send_json(message)
        except Exception as e:
            logger.error(f"Error sending personal message: {e}")
            self.disconnect(websocket)

    async def broadcast_flood_update(self, flood_data: Dict[str, Any]):
        """
        Broadcast flood data update to all connected clients.

        Args:
            flood_data: Dictionary containing river levels and weather data
        """
        if not self.active_connections:
            return  # No clients to broadcast to

        # Pre-convert ALL datetime objects to ISO format strings recursively
        clean_flood_data = convert_datetimes_to_strings(flood_data)

        message = {
            "type": "flood_update",
            "data": clean_flood_data,  # Now guaranteed to have no datetime objects
            "timestamp": datetime.now().isoformat(),
            "source": "flood_agent"
        }

        await self.broadcast(message)
        logger.info(f"Broadcasted flood update to {len(self.active_connections)} clients")

    async def broadcast_critical_alert(
        self,
        station_name: str,
        water_level: float,
        risk_level: str,
        message_text: str
    ):
        """
        Broadcast critical water level alert to all connected clients.

        Args:
            station_name: Name of the river station
            water_level: Current water level in meters
            risk_level: Risk classification (ALERT, ALARM, CRITICAL)
            message_text: Human-readable alert message
        """
        alert = {
            "type": "critical_alert",
            "severity": risk_level.lower(),
            "station": station_name,
            "water_level": water_level,
            "risk_level": risk_level,
            "message": message_text,
            "timestamp": datetime.now().isoformat(),  # Convert to string
            "action_required": risk_level in ["ALARM", "CRITICAL"]
        }

        await self.broadcast(alert)
        logger.warning(
            f"🚨 CRITICAL ALERT broadcasted: {station_name} - {risk_level} "
            f"({water_level}m) to {len(self.active_connections)} clients"
        )

    async def broadcast_scheduler_update(self, status: Dict[str, Any]):
        """
        Broadcast scheduler status update.

        Args:
            status: Scheduler status dictionary with run information
        """
        message = {
            "type": "scheduler_update",
            "status": status,
            "timestamp": datetime.now().isoformat()  # Convert to string
        }

        await self.broadcast(message)
        logger.debug(f"Broadcasted scheduler update to {len(self.active_connections)} clients")

    async def check_and_alert_critical_levels(self, flood_data: Dict[str, Any]):
        """
        Check flood data for critical water levels and broadcast alerts.

        Args:
            flood_data: Flood data from FloodAgent containing river levels
        """
        if "river_levels" not in flood_data:
            return

        river_levels = flood_data["river_levels"]

        for station_name, data in river_levels.items():
            risk_level = data.get("risk_level", "NORMAL")
            water_level = data.get("water_level", 0.0)

            # Alert on ALARM or CRITICAL levels
            if risk_level in ["ALARM", "CRITICAL"]:
                # Check if this is a new critical station
                station_key = f"{station_name}_{risk_level}"
                if station_key not in self.critical_stations:
                    self.critical_stations.add(station_key)

                    # Create alert message
                    if risk_level == "CRITICAL":
                        message = (
                            f"⚠️ CRITICAL FLOOD WARNING: {station_name} has reached "
                            f"CRITICAL water level ({water_level:.2f}m). "
                            f"EVACUATE IMMEDIATELY if you are in the affected area!"
                        )
                    else:  # ALARM
                        message = (
                            f"⚠️ FLOOD ALARM: {station_name} water level is at "
                            f"{water_level:.2f}m (ALARM level). "
                            f"Prepare for possible evacuation."
                        )

                    await self.broadcast_critical_alert(
                        station_name=station_name,
                        water_level=water_level,
                        risk_level=risk_level,
                        message_text=message
                    )

            # Clear from critical set if level drops below ALARM
            elif risk_level in ["NORMAL", "ALERT"]:
                # Remove all critical/alarm entries for this station
                to_remove = {
                    key for key in self.critical_stations
                    if key.startswith(station_name)
                }
                self.critical_stations -= to_remove

    async def broadcast_evacuation_update(self, evacuation_data: Dict[str, Any]):
        """
        Broadcast evacuation status update to all connected clients.

        Args:
            evacuation_data: Dictionary with evacuation mission status info
        """
        if not self.active_connections:
            return

        message = {
            "type": "evacuation_update",
            "data": convert_datetimes_to_strings(evacuation_data),
            "timestamp": datetime.now().isoformat(),
            "source": "evacuation_manager"
        }

        await self.broadcast(message)
        logger.info(f"Broadcasted evacuation update to {len(self.active_connections)} clients")

    async def broadcast_distress_alert(self, distress_data: Dict[str, Any]):
        """
        Broadcast a distress call alert to all connected clients.

        Args:
            distress_data: Dictionary with distress call details (location, urgency, etc.)
        """
        if not self.active_connections:
            return

        message = {
            "type": "distress_alert",
            "data": convert_datetimes_to_strings(distress_data),
            "timestamp": datetime.now().isoformat(),
            "source": "orchestrator"
        }

        await self.broadcast(message)
        logger.warning(
            f"Broadcasted distress alert to {len(self.active_connections)} clients"
        )
