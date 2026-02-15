"""
Google Places API proxy endpoints.

Migrated from Next.js API routes to FastAPI for static frontend export.
These endpoints proxy requests to the Google Maps API, keeping the
API key server-side.
"""

import logging
import httpx
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from app.core.config import settings

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/places", tags=["places"])


class AutocompleteRequest(BaseModel):
    input: str
    sessionToken: str
    components: str = "country:ph"


class DetailsRequest(BaseModel):
    placeId: str
    sessionToken: str
    fields: str = "formatted_address,geometry/location,name"


class GeocodeRequest(BaseModel):
    address: str
    components: str = "country:PH"


@router.post("/autocomplete")
async def places_autocomplete(req: AutocompleteRequest):
    if not settings.GOOGLE_API_KEY:
        raise HTTPException(status_code=500, detail="Google Maps API key is not configured.")

    if not req.input or len(req.input.strip()) < 3:
        return {"status": "ZERO_RESULTS", "predictions": []}

    params = {
        "input": req.input,
        "key": settings.GOOGLE_API_KEY,
        "sessiontoken": req.sessionToken,
        "components": req.components,
    }

    async with httpx.AsyncClient() as client:
        resp = await client.get(
            "https://maps.googleapis.com/maps/api/place/autocomplete/json",
            params=params,
        )

    if resp.status_code != 200:
        raise HTTPException(status_code=resp.status_code, detail="Autocomplete request failed.")

    return resp.json()


@router.post("/details")
async def places_details(req: DetailsRequest):
    if not settings.GOOGLE_API_KEY:
        raise HTTPException(status_code=500, detail="Google Maps API key is not configured.")

    params = {
        "place_id": req.placeId,
        "key": settings.GOOGLE_API_KEY,
        "sessiontoken": req.sessionToken,
        "fields": req.fields,
    }

    async with httpx.AsyncClient() as client:
        resp = await client.get(
            "https://maps.googleapis.com/maps/api/place/details/json",
            params=params,
        )

    if resp.status_code != 200:
        raise HTTPException(status_code=resp.status_code, detail="Place details request failed.")

    return resp.json()


@router.post("/geocode")
async def places_geocode(req: GeocodeRequest):
    if not settings.GOOGLE_API_KEY:
        raise HTTPException(status_code=500, detail="Google Maps API key is not configured.")

    if not req.address or len(req.address.strip()) < 3:
        return {"status": "ZERO_RESULTS", "results": []}

    params = {
        "address": req.address.strip(),
        "key": settings.GOOGLE_API_KEY,
        "components": req.components,
    }

    async with httpx.AsyncClient() as client:
        resp = await client.get(
            "https://maps.googleapis.com/maps/api/geocode/json",
            params=params,
        )

    if resp.status_code != 200:
        raise HTTPException(status_code=resp.status_code, detail="Geocoding request failed.")

    return resp.json()
