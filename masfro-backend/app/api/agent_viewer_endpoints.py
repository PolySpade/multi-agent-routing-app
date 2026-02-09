# filename: app/api/agent_viewer_endpoints.py

from fastapi import APIRouter, HTTPException, Depends, Body, UploadFile, File, Form
from typing import List, Dict, Any, Optional
import tempfile
import os
from pathlib import Path

from app.services.agent_viewer_service import get_agent_viewer_service, AgentViewerService

router = APIRouter(prefix="/agents", tags=["Agent Viewer"])


@router.get("/", response_model=List[Dict[str, Any]])
async def get_agents(service: AgentViewerService = Depends(get_agent_viewer_service)):
    """
    Get a list of all active agents and their real status.
    """
    return service.get_agents_status()


@router.get("/logs", response_model=List[Dict[str, Any]])
async def get_logs(
    limit: int = 50,
    agent_id: Optional[str] = None,
    level: Optional[str] = None,
    service: AgentViewerService = Depends(get_agent_viewer_service),
):
    """
    Get recent logs, optionally filtered by agent ID and/or minimum log level.

    - **level**: Minimum severity — DEBUG, INFO, WARNING, ERROR, or CRITICAL.
    """
    return service.get_recent_logs(limit=limit, agent_id=agent_id, level=level)


@router.post("/scout/inject")
async def inject_tweet(
    text: str = Form(""),
    image: Optional[UploadFile] = File(None),
    service: AgentViewerService = Depends(get_agent_viewer_service),
):
    """
    Inject a manual tweet into the Scout Agent.

    - **text**: Tweet text content (optional, can be empty for image-only)
    - **image**: Optional image file for visual analysis

    Note: At least one of text or image should be provided for meaningful processing.
    """
    scout_agent = service.get_agent("scout")
    if not scout_agent:
        raise HTTPException(status_code=503, detail="Scout Agent not initialized")

    # Validate at least one input is provided
    has_image = image and image.filename
    if not text.strip() and not has_image:
        raise HTTPException(
            status_code=400,
            detail="At least one of text or image must be provided"
        )

    payload = {"text": text}

    # Handle image upload if provided
    if has_image:
        # Create temp directory for uploads if it doesn't exist
        upload_dir = Path(tempfile.gettempdir()) / "masfro_uploads"
        upload_dir.mkdir(exist_ok=True)

        # Save uploaded file with unique name
        file_ext = os.path.splitext(image.filename)[1] or ".jpg"
        temp_path = upload_dir / f"tweet_image_{os.urandom(8).hex()}{file_ext}"

        try:
            contents = await image.read()
            with open(temp_path, "wb") as f:
                f.write(contents)
            payload["image_path"] = str(temp_path)
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to save image: {e}")

    result = scout_agent.inject_manual_tweet(payload)
    if isinstance(result, dict) and result.get("status") == "error":
        raise HTTPException(status_code=400, detail=result.get("message", "Unknown error"))

    return {"status": "success", "processed_data": result}


@router.post("/flood/inject")
async def inject_advisory(
    payload: Dict[str, Any] = Body(...),
    service: AgentViewerService = Depends(get_agent_viewer_service),
):
    """
    Inject a manual advisory/news into the Flood Agent.
    Payload should contain: text, [type], [severity]
    """
    flood_agent = service.get_agent("flood")
    if not flood_agent:
        raise HTTPException(status_code=503, detail="Flood Agent not initialized")

    result = flood_agent.inject_manual_advisory(payload)
    if isinstance(result, dict) and result.get("status") == "error":
        raise HTTPException(status_code=400, detail=result.get("message", "Unknown error"))

    return result
