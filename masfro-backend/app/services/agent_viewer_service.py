# filename: app/services/agent_viewer_service.py

import logging
from typing import List, Dict, Any, Optional
from collections import deque
from datetime import datetime

# Valid log levels for filtering
_VALID_LEVELS = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}

# Map each agent role to its real status method
_STATUS_METHODS = {
    'scout': 'get_processing_stats',
    'flood': 'get_agent_stats',
    'routing': 'get_statistics',
    'evacuation': 'get_route_statistics',
    'hazard': 'get_agent_stats',
    'orchestrator': 'get_system_status',
}


class LogCaptureHandler(logging.Handler):
    """
    Custom logging handler that stores the last N log records in memory.

    Capacity increased from 1000 to 5000 to handle:
    - Burst logging during startup/initialization
    - Multiple agents logging simultaneously
    - Retaining scout/flood logs when hazard agent logs frequently
    """
    def __init__(self, capacity: int = 5000):
        super().__init__()
        self.capacity = capacity
        self.logs: deque = deque(maxlen=capacity)

    def emit(self, record: logging.LogRecord):
        try:
            entry = {
                "timestamp": datetime.fromtimestamp(record.created).isoformat(),
                "level": record.levelname,
                "logger": record.name,
                "message": record.getMessage(),
            }
            self.logs.append(entry)
        except Exception:
            self.handleError(record)

    def get_logs(
        self,
        limit: int = 100,
        logger_filter: Optional[str] = None,
        level_filter: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        Retrieve logs, optionally filtered by logger name and/or minimum level.
        """
        all_logs = list(self.logs)

        if logger_filter:
            all_logs = [log for log in all_logs if logger_filter in log["logger"]]

        if level_filter and level_filter in _VALID_LEVELS:
            min_severity = getattr(logging, level_filter)
            all_logs = [
                log for log in all_logs
                if getattr(logging, log["level"], 0) >= min_severity
            ]

        return all_logs[-limit:]


class AgentViewerService:
    """
    Service to manage agent log viewing and manual interaction.
    Holds a registry of live agent references for status checks and injection.
    """
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(AgentViewerService, cls).__new__(cls)
            cls._instance.handler = LogCaptureHandler()
            cls._instance._agents: Dict[str, Any] = {}
            cls._instance.setup_logging()
        return cls._instance

    def setup_logging(self):
        """
        Attaches the capture handler to 'app' and 'app.agents' loggers.
        Both are needed because app.agents has propagate=False.

        IMPORTANT: Call this AFTER logging.config.dictConfig() has been applied,
        as dictConfig replaces all handlers on loggers.
        """
        app_logger = logging.getLogger("app")
        agents_logger = logging.getLogger("app.agents")

        # Remove any existing instances of our handler to avoid duplicates
        for logger in [app_logger, agents_logger]:
            logger.handlers = [h for h in logger.handlers if not isinstance(h, LogCaptureHandler)]
            logger.addHandler(self.handler)

    def register_agents(self, agents: Dict[str, Any]) -> None:
        """
        Register live agent instances (called once from main.py after init).

        Args:
            agents: Dict of {'role': agent_instance}, e.g.
                     {'scout': scout_agent, 'flood': flood_agent, ...}
        """
        self._agents = agents

    def get_agent(self, role: str) -> Optional[Any]:
        """Get a registered agent by role name."""
        return self._agents.get(role)

    def get_recent_logs(
        self,
        limit: int = 50,
        agent_id: Optional[str] = None,
        level: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        filter_str = f"app.agents.{agent_id}" if agent_id else None
        return self.handler.get_logs(limit=limit, logger_filter=filter_str, level_filter=level)

    def get_agents_status(self) -> List[Dict[str, Any]]:
        """Query each registered agent for its real status."""
        results = []
        for role, agent in self._agents.items():
            entry = {
                "id": getattr(agent, "agent_id", role),
                "type": type(agent).__name__,
            }
            method_name = _STATUS_METHODS.get(role)
            if method_name and hasattr(agent, method_name):
                try:
                    entry["status"] = "Active"
                    entry["details"] = getattr(agent, method_name)()
                except Exception as e:
                    entry["status"] = "Error"
                    entry["details"] = {"error": str(e)}
            else:
                entry["status"] = "Active"
            results.append(entry)
        return results


# Global instance getter
def get_agent_viewer_service() -> AgentViewerService:
    return AgentViewerService()
