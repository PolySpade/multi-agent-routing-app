# filename: masfro-backend/main.py

from fastapi import FastAPI
from pydantic import BaseModel
from typing import List, Tuple
from fastapi import BackgroundTasks # for handling background agents

#Agent Functions
from app.environment.graph_manager import DynamicGraphEnvironment

# --- 1. Data Models (using Pydantic) ---
# This defines the expected JSON structure for a request to the /api/route endpoint.
# FastAPI will automatically validate incoming data against this model.
class RouteRequest(BaseModel):
    start_location: Tuple[float, float] # e.g., (14.62, 121.12)
    end_location: Tuple[float, float]

# --- 2. Core Simulation Components (Placeholders) ---
# These are the classes from your methodology. For now, they are simple placeholders.

# class DynamicGraphEnvironment:
#     """
#     Manages the road network graph (using NetworkX and OSMnx).
#     This class will load the map data and handle dynamic updates to edge weights (risk scores).
#     """
#     def __init__(self):
#         # TODO: Implement graph loading from OSMnx as per Section 4.4.2.
#         print("DynamicGraphEnvironment initialized.")
#         self.graph = None # This will hold the NetworkX graph object.

class RoutingAgent:
    """
    Responsible for computing the safest and most efficient path.
    It queries the DynamicGraphEnvironment to perform its calculations.
    """
    def __init__(self, environment: DynamicGraphEnvironment):
        # The agent needs a reference to the environment to access the graph.
        self.environment = environment
        print("RoutingAgent initialized.")

    def find_safest_route(self, start_node, end_node) -> List[Tuple[float, float]]:
        """
        Calculates the optimal route based on risk and distance.
        # TODO: Implement the risk-aware A* algorithm described in your paper.
        """
        print(f"Finding route from {start_node} to {end_node}...")
        # For now, return a hardcoded placeholder path for testing.
        return [
            (14.6231, 121.1011), # Placeholder coordinate 1
            (14.6245, 121.1023), # Placeholder coordinate 2
            (14.6258, 121.1035)  # Placeholder coordinate 3
        ]

# --- 3. FastAPI Application Setup ---

# Create the main FastAPI application instance.
app = FastAPI(
    title="MAS-FRO API",
    description="API for the Multi-Agent System for Flood Route Optimization.",
    version="0.1.0"
)

# Create single, shared instances of your core components.
# This ensures that all API requests use the same environment and agent objects.
environment = DynamicGraphEnvironment()
routing_agent = RoutingAgent(environment)

# --- 4. API Endpoints ---
@app.post("/api/route", tags=["Routing"])
async def get_route(request: RouteRequest) -> dict:
    """
    Accepts start and end coordinates and returns the safest calculated route.
    """
    # The `request` object is an instance of `RouteRequest` with validated data.
    path = routing_agent.find_safest_route(
        start_node=request.start_location,
        end_node=request.end_location
    )
    
    return {"status": "success", "path": path}

@app.get("/", tags=["General"])
async def read_root():
    """A simple endpoint to check if the server is running."""
    return {"message": "Welcome to the MAS-FRO Backend API"}




# @app.post("/api/admin/update-hazards", tags=["Admin"])
# async def trigger_hazard_updates(background_tasks: BackgroundTasks):
#     """
#     Triggers the background agents to scrape for the latest hazard data.
#     This endpoint returns immediately.
#     """
#     print("API CALL: Received request to update hazard data.")

#     # Add the scraping functions to the background tasks queue
#     # Pass the shared 'environment' object so the agent can update it
#     background_tasks.add_task(scrape_pagasa_rainfall_data, environment)
#     # background_tasks.add_task(scrape_social_media_data, environment) # For your scout agent

#     return {"message": "Hazard data update process started in the background."}