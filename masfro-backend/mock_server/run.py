"""
Convenience runner for the mock data server.

Usage:
    cd masfro-backend-v2
    python -m mock_server.run
    python -m mock_server.run --port 8081
    python -m mock_server.run --scenario heavy
"""

import argparse
import uvicorn

import mock_server


def main():
    parser = argparse.ArgumentParser(description="MAS-FRO Mock Data Server")
    parser.add_argument("--host", default="0.0.0.0", help="Host to bind to")
    parser.add_argument("--port", type=int, default=8081, help="Port to listen on")
    parser.add_argument("--scenario", default="light", choices=["light", "medium", "heavy"],
                        help="Initial scenario to load")
    parser.add_argument("--reload", action="store_true", help="Enable auto-reload")
    args = parser.parse_args()

    # Store the chosen scenario so the startup handler in main.py uses it
    # instead of always defaulting to "light".
    mock_server._initial_scenario = args.scenario

    uvicorn.run(
        "mock_server.main:app",
        host=args.host,
        port=args.port,
        reload=args.reload,
    )


if __name__ == "__main__":
    main()
