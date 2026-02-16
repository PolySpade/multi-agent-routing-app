"""
Graph Risk Visualization API Routes

Provides endpoints for exposing graph edge risk scores in GeoJSON format
for frontend visualization on interactive maps.
"""

from fastapi import APIRouter, HTTPException, Query
from typing import Dict, Any, List, Optional
import logging

router = APIRouter(prefix="/api/graph", tags=["graph"])
logger = logging.getLogger(__name__)

# Global reference to environment (set by main.py)
_graph_environment = None


def set_graph_environment(env):
    """Set the global graph environment instance."""
    global _graph_environment
    _graph_environment = env


def get_graph_environment():
    """Get the global graph environment instance."""
    if _graph_environment is None:
        raise HTTPException(
            status_code=503,
            detail="Graph environment not initialized. Please start the server properly."
        )
    return _graph_environment


@router.get("/edges/geojson")
async def get_graph_edges_geojson(
    min_risk: Optional[float] = Query(
        None, ge=0.0, le=1.0, description="Minimum risk score to include"
    ),
    max_risk: Optional[float] = Query(
        None, ge=0.0, le=1.0, description="Maximum risk score to include"
    ),
    sample_size: Optional[int] = Query(
        None, ge=100, le=50000, description="Number of edges to return (sampling)"
    ),
) -> Dict[str, Any]:
    """
    Get graph edges with risk scores in GeoJSON format for map visualization.

    Args:
        min_risk: Filter edges with risk >= this value
        max_risk: Filter edges with risk <= this value
        sample_size: Limit number of edges returned (for performance)

    Returns:
        GeoJSON FeatureCollection with LineString features
    """
    try:
        logger.info("Fetching graph edges for GeoJSON conversion")

        # Get graph environment
        env = get_graph_environment()
        graph = env.graph

        # Get all edges first for proper sampling
        all_edges = list(graph.edges(data=True))

        # Apply connectivity-preserving sampling if sample_size is specified
        if sample_size and sample_size < len(all_edges):
            # Strategy: Use BFS to sample connected subgraphs for better visualization
            import random
            import networkx as nx

            sampled_edges = []
            visited_edges = set()
            edges_dict = {(u, v): data for u, v, data in all_edges}

            # Calculate how many starting points we need for good coverage
            # More starting points = better geographic distribution
            num_clusters = max(1, sample_size // 100)  # ~100 edges per cluster

            # Select random starting nodes distributed across the graph
            all_nodes = list(graph.nodes())
            start_nodes = random.sample(all_nodes, min(num_clusters, len(all_nodes)))

            logger.info(f"Sampling {sample_size} connected edges from {len(all_edges)} total using {num_clusters} clusters")

            for start_node in start_nodes:
                if len(sampled_edges) >= sample_size:
                    break

                # BFS from this starting node to get connected edges
                visited_nodes = {start_node}
                queue = [start_node]
                cluster_edges = []

                while queue and len(sampled_edges) + len(cluster_edges) < sample_size:
                    current = queue.pop(0)

                    # Get neighbors
                    for neighbor in graph.neighbors(current):
                        edge_key = (current, neighbor)
                        edge_key_rev = (neighbor, current)

                        # Check if edge already sampled
                        if edge_key in visited_edges or edge_key_rev in visited_edges:
                            continue

                        # Add edge to cluster
                        if edge_key in edges_dict:
                            cluster_edges.append((current, neighbor, edges_dict[edge_key]))
                            visited_edges.add(edge_key)
                        elif edge_key_rev in edges_dict:
                            cluster_edges.append((neighbor, current, edges_dict[edge_key_rev]))
                            visited_edges.add(edge_key_rev)

                        # Add neighbor to queue if not visited
                        if neighbor not in visited_nodes:
                            visited_nodes.add(neighbor)
                            queue.append(neighbor)

                        # Stop if we have enough edges
                        if len(sampled_edges) + len(cluster_edges) >= sample_size:
                            break

                sampled_edges.extend(cluster_edges)

            # Truncate to exact sample size
            sampled_edges = sampled_edges[:sample_size]
            logger.info(f"Sampled {len(sampled_edges)} connected edges forming coherent road segments")
        else:
            sampled_edges = all_edges
            logger.info(f"Returning all {len(all_edges)} edges (no sampling)")

        # Collect edge features
        features = []
        edge_count = 0

        for u, v, data in sampled_edges:
            # Get risk score
            risk_score = data.get("risk_score", 0.0)

            # Apply risk filters
            if min_risk is not None and risk_score < min_risk:
                continue
            if max_risk is not None and risk_score > max_risk:
                continue

            # Get node coordinates
            u_data = graph.nodes[u]
            v_data = graph.nodes[v]

            if "x" not in u_data or "y" not in u_data:
                continue
            if "x" not in v_data or "y" not in v_data:
                continue

            # Create GeoJSON LineString feature
            feature = {
                "type": "Feature",
                "geometry": {
                    "type": "LineString",
                    "coordinates": [
                        [u_data["x"], u_data["y"]],  # [lng, lat]
                        [v_data["x"], v_data["y"]],
                    ],
                },
                "properties": {
                    "edge_id": f"{u}-{v}",
                    "risk_score": float(risk_score),
                    "risk_category": _get_risk_category(risk_score),
                    "length": data.get("length", 0.0),
                    "highway": data.get("highway", "unknown"),
                    "flood_depth": round(float(data.get("flood_depth", 0.0)), 3),
                    "name": data.get("name", ""),
                },
            }

            features.append(feature)
            edge_count += 1

        # Create GeoJSON FeatureCollection
        geojson = {
            "type": "FeatureCollection",
            "features": features,
            "properties": {
                "total_edges": edge_count,
                "sampled": sample_size is not None,
                "filters": {
                    "min_risk": min_risk,
                    "max_risk": max_risk,
                },
            },
        }

        logger.info(f"Returning {edge_count} edges as GeoJSON")
        return geojson

    except Exception as e:
        logger.error(f"Error generating GeoJSON: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to generate GeoJSON: {str(e)}")


@router.get("/statistics")
async def get_graph_statistics() -> Dict[str, Any]:
    """
    Get current graph risk statistics.

    Returns:
        Dictionary with statistical summary
    """
    try:
        logger.info("Fetching graph statistics")

        env = get_graph_environment()
        graph = env.graph

        # Collect risk scores
        risk_scores = []
        for _, _, data in graph.edges(data=True):
            risk_scores.append(data.get("risk_score", 0.0))

        if not risk_scores:
            return {
                "total_edges": 0,
                "statistics": {},
            }

        # Calculate statistics
        import numpy as np

        risk_array = np.array(risk_scores)

        statistics = {
            "total_edges": len(risk_scores),
            "avg_risk_score": float(np.mean(risk_array)),
            "median_risk_score": float(np.median(risk_array)),
            "max_risk_score": float(np.max(risk_array)),
            "min_risk_score": float(np.min(risk_array)),
            "std_risk_score": float(np.std(risk_array)),
            "low_risk_edges": int(np.sum(risk_array < 0.3)),
            "medium_risk_edges": int(np.sum((risk_array >= 0.3) & (risk_array < 0.6))),
            "high_risk_edges": int(np.sum(risk_array >= 0.6)),
            "risk_distribution": {
                "0.0-0.1": int(np.sum((risk_array >= 0.0) & (risk_array < 0.1))),
                "0.1-0.2": int(np.sum((risk_array >= 0.1) & (risk_array < 0.2))),
                "0.2-0.3": int(np.sum((risk_array >= 0.2) & (risk_array < 0.3))),
                "0.3-0.4": int(np.sum((risk_array >= 0.3) & (risk_array < 0.4))),
                "0.4-0.5": int(np.sum((risk_array >= 0.4) & (risk_array < 0.5))),
                "0.5-0.6": int(np.sum((risk_array >= 0.5) & (risk_array < 0.6))),
                "0.6-0.7": int(np.sum((risk_array >= 0.6) & (risk_array < 0.7))),
                "0.7-0.8": int(np.sum((risk_array >= 0.7) & (risk_array < 0.8))),
                "0.8-0.9": int(np.sum((risk_array >= 0.8) & (risk_array < 0.9))),
                "0.9-1.0": int(np.sum((risk_array >= 0.9) & (risk_array <= 1.0))),
            },
        }

        logger.info(f"Graph statistics: {statistics['total_edges']} edges, avg risk: {statistics['avg_risk_score']:.4f}")
        return statistics

    except Exception as e:
        logger.error(f"Error calculating statistics: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to calculate statistics: {str(e)}")


def _get_risk_category(risk_score: float) -> str:
    """
    Categorize risk score into low/medium/high.

    Args:
        risk_score: Risk score (0.0-1.0)

    Returns:
        Category string
    """
    if risk_score < 0.3:
        return "low"
    elif risk_score < 0.6:
        return "medium"
    else:
        return "high"
