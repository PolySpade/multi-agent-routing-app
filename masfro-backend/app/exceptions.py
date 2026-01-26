"""
Custom exception hierarchy for MAS-FRO system.

Provides specific exception types for different failure modes
to enable better error handling and debugging.
"""


class MASFROException(Exception):
    """Base exception for all MAS-FRO system errors."""
    pass


# === Agent Communication Exceptions ===

class AgentCommunicationError(MASFROException):
    """Agent-to-agent communication failures."""
    pass


class MessageQueueError(AgentCommunicationError):
    """Message queue operation failures."""
    pass


class ACLProtocolError(AgentCommunicationError):
    """FIPA-ACL protocol violations."""
    def __init__(self, message: str, performative: str = None):
        self.performative = performative
        super().__init__(message)


# === Data Collection Exceptions ===

class DataCollectionError(MASFROException):
    """Base exception for data collection failures."""
    pass


class APITimeoutError(DataCollectionError):
    """API request timeout."""
    def __init__(self, service: str, timeout_seconds: float):
        self.service = service
        self.timeout_seconds = timeout_seconds
        super().__init__(
            f"{service} API timeout after {timeout_seconds}s"
        )


class APIResponseError(DataCollectionError):
    """Invalid API response received."""
    def __init__(self, service: str, status_code: int, message: str = ""):
        self.service = service
        self.status_code = status_code
        super().__init__(
            f"{service} API error (status {status_code}): {message}"
        )


class DataParsingError(DataCollectionError):
    """Failed to parse data from external source."""
    def __init__(self, source: str, data_type: str, details: str = ""):
        self.source = source
        self.data_type = data_type
        super().__init__(
            f"Failed to parse {data_type} from {source}: {details}"
        )


# === Routing & Pathfinding Exceptions ===

class RouteCalculationError(MASFROException):
    """Route calculation failures."""
    pass


class NoPathFoundError(RouteCalculationError):
    """No valid path exists between origin and destination."""
    def __init__(self, origin: tuple, destination: tuple, reason: str = ""):
        self.origin = origin
        self.destination = destination
        super().__init__(
            f"No path found from {origin} to {destination}. {reason}"
        )


class InvalidLocationError(RouteCalculationError):
    """Invalid geographic coordinates provided."""
    def __init__(self, location: tuple, reason: str = ""):
        self.location = location
        super().__init__(
            f"Invalid location {location}: {reason}"
        )


# === Graph Environment Exceptions ===

class GraphEnvironmentError(MASFROException):
    """Graph environment operation failures."""
    pass


class GraphNotLoadedError(GraphEnvironmentError):
    """Graph environment not initialized or loaded."""
    pass


class GraphUpdateError(GraphEnvironmentError):
    """Failed to update graph edge weights or attributes."""
    def __init__(self, edge: tuple, reason: str = ""):
        self.edge = edge
        super().__init__(
            f"Failed to update edge {edge}: {reason}"
        )


# === GeoTIFF & Spatial Data Exceptions ===

class GeoSpatialError(MASFROException):
    """Geospatial data processing errors."""
    pass


class GeoTIFFLoadError(GeoSpatialError):
    """Failed to load GeoTIFF file."""
    def __init__(self, filepath: str, reason: str = ""):
        self.filepath = filepath
        super().__init__(
            f"Failed to load GeoTIFF {filepath}: {reason}"
        )


class CoordinateTransformError(GeoSpatialError):
    """Coordinate system transformation failed."""
    pass


# === Configuration Exceptions ===

class ConfigurationError(MASFROException):
    """System configuration errors."""
    pass


class MissingCredentialError(ConfigurationError):
    """Required credentials not found in environment."""
    def __init__(self, credential_name: str):
        self.credential_name = credential_name
        super().__init__(
            f"Missing required credential: {credential_name}. "
            f"Please set in environment variables or .env file."
        )


class InvalidConfigError(ConfigurationError):
    """Invalid configuration value."""
    def __init__(self, config_key: str, value: any, reason: str = ""):
        self.config_key = config_key
        self.value = value
        super().__init__(
            f"Invalid configuration for {config_key}={value}: {reason}"
        )


# === Database Exceptions ===

class DatabaseError(MASFROException):
    """Database operation failures."""
    pass


class DatabaseConnectionError(DatabaseError):
    """Failed to connect to database."""
    pass


class DataPersistenceError(DatabaseError):
    """Failed to save or retrieve data from database."""
    pass
