"""
Simulation control API endpoints.
"""

import logging
from datetime import datetime
from fastapi import APIRouter, HTTPException, Depends, Query

from app.services.simulation_manager import get_simulation_manager
from app.core.dependencies import get_websocket_manager, get_environment
from app.core.auth import verify_api_key

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Simulation"])


@router.post("/start")
async def start_simulation(
    mode: str = Query(
        "light",
        description="Simulation mode: light, medium, or heavy"
    ),
    ws_manager=Depends(get_websocket_manager)
):
    """
    Start the simulation with specified flood scenario mode.

    Args:
        mode: Simulation mode (light, medium, heavy)
            - light: < 0.5m depth, low risk areas
            - medium: 0.5m - 1.0m depth, moderate risk
            - heavy: > 1.0m depth, high risk zones

    Returns:
        Simulation start result with state information
    """
    logger.info(f"Simulation start request received - Mode: {mode}")

    try:
        sim_manager = get_simulation_manager()
        result = await sim_manager.start(mode=mode)

        # Broadcast simulation state change via WebSocket
        await ws_manager.broadcast({
            "type": "simulation_state",
            "event": "started",
            "data": result,
            "timestamp": datetime.now().isoformat()
        })

        logger.info(
            f"Simulation started successfully - "
            f"Mode: {result['mode']}, State: {result['state']}"
        )

        return result

    except ValueError as e:
        logger.warning(f"Invalid simulation start request: {e}")
        raise HTTPException(
            status_code=400,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error starting simulation: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Error starting simulation: {str(e)}"
        )


@router.post("/stop")
async def stop_simulation(
    ws_manager=Depends(get_websocket_manager)
):
    """
    Stop (pause) the currently running simulation.

    This endpoint pauses the simulation and stops data input processing.
    The simulation state is preserved and can be resumed with start.

    Returns:
        Simulation stop result with runtime information
    """
    logger.info("Simulation stop request received")

    try:
        sim_manager = get_simulation_manager()
        result = await sim_manager.stop()

        # Broadcast simulation state change via WebSocket
        await ws_manager.broadcast({
            "type": "simulation_state",
            "event": "stopped",
            "data": result,
            "timestamp": datetime.now().isoformat()
        })

        logger.info(
            f"Simulation stopped successfully - "
            f"Runtime: {result['total_runtime_seconds']}s"
        )

        return result

    except ValueError as e:
        logger.warning(f"Invalid simulation stop request: {e}")
        raise HTTPException(
            status_code=400,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error stopping simulation: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Error stopping simulation: {str(e)}"
        )


@router.post("/reset")
async def reset_simulation(
    ws_manager=Depends(get_websocket_manager),
    environment=Depends(get_environment)
):
    """
    Reset the simulation to initial state.

    This endpoint:
    - Resets simulation state to STOPPED
    - Clears all simulation data
    - Resets runtime counters
    - Resets mode to LIGHT
    - Clears graph risk scores (resets to baseline)

    Returns:
        Simulation reset result with previous state information
    """
    logger.info("Simulation reset request received")

    try:
        sim_manager = get_simulation_manager()
        result = await sim_manager.reset()

        # Reset graph to baseline (clear all risk scores)
        if environment.graph:
            logger.info("Resetting graph risk scores to baseline")
            # Reset all edge risk scores to 0.0
            for u, v, key in environment.graph.edges(keys=True):
                environment.graph[u][v][key]["risk_score"] = 0.0
            logger.info(f"Reset {environment.graph.number_of_edges()} edges to baseline risk")

        # Broadcast simulation state change via WebSocket
        await ws_manager.broadcast({
            "type": "simulation_state",
            "event": "reset",
            "data": result,
            "timestamp": datetime.now().isoformat()
        })

        logger.info(
            f"Simulation reset successfully - "
            f"Previous state: {result['previous_state']}, "
            f"Previous runtime: {result['previous_runtime_seconds']}s"
        )

        return result

    except Exception as e:
        logger.error(f"Error resetting simulation: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Error resetting simulation: {str(e)}"
        )


@router.get("/status")
async def get_simulation_status():
    """
    Get current simulation status and state.

    Returns comprehensive information about:
    - Current state (stopped, running, paused)
    - Current mode (light, medium, heavy)
    - Runtime statistics
    - Start/pause timestamps

    Returns:
        Complete simulation status information
    """
    try:
        sim_manager = get_simulation_manager()
        status = sim_manager.get_status()

        return {
            "status": "success",
            "simulation": status,
            "timestamp": datetime.now().isoformat()
        }

    except Exception as e:
        logger.error(f"Error retrieving simulation status: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Error retrieving simulation status: {str(e)}"
        )
