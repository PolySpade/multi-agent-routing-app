import os
import sys
import logging
from pathlib import Path
import matplotlib.pyplot as plt
import networkx as nx
import osmnx as ox
import numpy as np
import rasterio

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.environment.graph_manager import DynamicGraphEnvironment
from app.services.geotiff_service import get_geotiff_service

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("FloodVisualizer")

def visualize_flood_map(return_period="rr01", time_step=1, output_file="flood_heatmap.png"):
    """
    Generate a heatmap of flood depths overlaid on the street network.
    """
    logger.info(f"Initializing visualization for {return_period} step {time_step}...")
    
    # 1. Load Graph
    logger.info("Loading street network...")
    env = DynamicGraphEnvironment()
    if not env.graph:
        logger.error("Failed to load graph!")
        return

    # 2. Load GeoTIFF Data
    logger.info(f"Loading flood data from {return_period} step {time_step}...")
    geotiff_service = get_geotiff_service()
    try:
        flood_data, metadata = geotiff_service.load_flood_map(return_period, time_step)
        transform = metadata['transform'] # Affine transform
    except Exception as e:
        logger.error(f"Failed to load GeoTIFF: {e}")
        return

    # 3. Map Flood Depths to Edges
    logger.info("Mapping flood depths to network edges...")
    edge_colors = []
    max_depth = 0
    
    # Iterate through edges
    edges = []
    for u, v, k, data in env.graph.edges(keys=True, data=True):
        # Get edge midpoint
        u_node = env.graph.nodes[u]
        v_node = env.graph.nodes[v]
        mid_lon = (u_node['x'] + v_node['x']) / 2
        mid_lat = (u_node['y'] + v_node['y']) / 2
        
        # Get flood depth from service (handles manual coordinate mapping internally)
        depth = geotiff_service.get_flood_depth_at_point(
            mid_lon, mid_lat, return_period, time_step
        )
        
        if depth is None:
            depth = 0.0
        
        if depth > max_depth:
            max_depth = depth
            
        edge_colors.append(depth)
        edges.append((u, v, k))

    logger.info(f"Max flood depth detected on network: {max_depth:.2f}m")

    # 4. Plot
    # 4. Plot
    logger.info("Generating plot (this may take a moment)...")
    
    # Manually map depths to colors (OSMnx 2.x compatibility)
    import matplotlib.colors as mcolors
    import matplotlib.cm as cm
    
    # Normalize depths: 0 to max_depth (or at least 2.0m for consistency)
    norm_max = max(max_depth, 2.0) 
    norm = mcolors.Normalize(vmin=0, vmax=norm_max)
    cmap = plt.get_cmap('YlOrRd')
    
    # Convert depth values to rgba colors
    final_edge_colors = []
    passable_color = mcolors.to_rgba('#333333') # Convert to RGBA
    
    for depth in edge_colors:
        if depth <= 0.01:
            final_edge_colors.append(passable_color) # Dark grey for safely passable
        else:
            final_edge_colors.append(cmap(norm(depth)))
            
    fig, ax = ox.plot_graph(
        env.graph,
        node_size=0,
        edge_color=final_edge_colors,
        edge_linewidth=2,
        bgcolor='black',
        show=False,
        close=False,
        figsize=(12, 12)
    )
    
    # Add title and annotation
    plt.title(f"Flood Risk Heatmap - {return_period} (Step {time_step})", color='white', fontsize=16)
    plt.annotate(
        f"Max Depth: {max_depth:.2f}m\nSee {output_file}", 
        xy=(0.02, 0.02), 
        xycoords='axes fraction',
        color='white'
    )

    # 5. Save
    output_path = Path("visualizations") / output_file
    output_path.parent.mkdir(exist_ok=True)
    
    plt.savefig(output_path, dpi=300, bbox_inches='tight', facecolor='black')
    logger.info(f"✅ Visualization saved to {os.path.abspath(output_path)}")
    plt.close()

if __name__ == "__main__":
    # Create multiple visualizations
    visualize_flood_map("rr01", 1, "flood_map_start.png")
    visualize_flood_map("rr01", 10, "flood_map_peak.png") # Assuming peak is later
