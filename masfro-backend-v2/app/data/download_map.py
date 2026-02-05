# filename: masfro-backend/download_map.py
import osmnx as ox
import networkx as nx
import argparse
import logging
import sys
from pathlib import Path

# Configure Logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)

def get_custom_filter():
    """
    Returns the strict custom filter for OSM queries.
    """
    # COMPREHENSIVE CUSTOM FILTER: Include ALL road types
    # Syntax note: These strings are implicitly concatenated by Python
    return (
        '["highway"]["area"!~"yes"]'                                     # All highways, excluding areas
        '["highway"!~"proposed|construction|abandoned|platform|raceway"]' # Exclude invalid types
        '["service"!~"parking|parking_aisle|driveway"]'                   # Exclude private parking
    )

def enrich_graph_data(graph):
    """
    Adds speed and travel time data to the graph.
    Fills missing maxspeed data with defaults based on road type.
    """
    logger.info("⚡ Enriching graph with speed and travel times...")
    
    # Add edge speeds (km/h) - imputes missing values based on highway type
    # e.g. residential = 30km/h, primary = 50km/h
    graph = ox.add_edge_speeds(graph)
    
    # Add travel times (seconds)
    graph = ox.add_edge_travel_times(graph)
    
    return graph

def save_visualization(graph, place_name, output_dir):
    """
    Saves a static PNG image of the graph for visual verification.
    """
    image_path = output_dir / "graph_preview.png"
    logger.info(f"📸 Saving visual preview to {image_path}...")
    
    try:
        ox.plot_graph(
            graph, 
            filepath=image_path, 
            save=True, 
            show=False, 
            node_size=0, 
            edge_linewidth=0.5, 
            dpi=300
        )
    except Exception as e:
        logger.warning(f"Could not save visualization: {e}")

def print_statistics(graph, projected_graph):
    """
    Prints comprehensive statistics about the downloaded graph.
    Uses the projected graph for accurate metric measurements.
    """
    nodes = graph.number_of_nodes()
    edges = graph.number_of_edges()
    
    # Calculate total length in kilometers
    total_length_m = sum(d['length'] for u, v, d in projected_graph.edges(data=True))
    total_length_km = total_length_m / 1000

    logger.info("📊 Graph Statistics:")
    logger.info(f"   - Nodes: {nodes:,}")
    logger.info(f"   - Edges: {edges:,}")
    logger.info(f"   - Total Road Length: {total_length_km:,.2f} km")

    # Breakdown by highway type
    highway_types = {}
    for u, v, data in graph.edges(data=True):
        hwy = data.get('highway', 'unknown')
        if isinstance(hwy, list):
            hwy = hwy[0]
        highway_types[hwy] = highway_types.get(hwy, 0) + 1

    logger.info("🛣️  Road Type Breakdown:")
    for hwy_type, count in sorted(highway_types.items(), key=lambda x: x[1], reverse=True):
        logger.info(f"   - {hwy_type}: {count:,}")

def download_and_save_graph(place_name, output_path, simplify=False):
    """
    Main execution logic.
    """
    output_file = Path(output_path)
    output_dir = output_file.parent
    
    # Ensure directory exists
    output_dir.mkdir(parents=True, exist_ok=True)

    logger.info(f"--- Starting download for: {place_name} ---")
    
    # OSMnx Settings
    ox.settings.user_agent = "MasfroBackend/1.0 (Research Project; contact: admin@masfro)"
    ox.settings.log_console = False
    ox.settings.use_cache = True

    try:
        # 1. Geocode
        logger.info("📍 Geocoding place boundary...")
        gdf = ox.geocode_to_gdf(place_name)
        polygon = gdf.union_all()

        # 2. Download
        logger.info("📥 Downloading network (this may take a moment)...")
        graph = ox.graph_from_polygon(
            polygon,
            custom_filter=get_custom_filter(),
            simplify=simplify,          # FALSE = maintain exact geometry (good for flooding)
            retain_all=True,            # TRUE = keep disconnected islands
            truncate_by_edge=True
        )

        if graph.number_of_edges() == 0:
            logger.error("❌ FAILURE: Graph is empty.")
            return

        # 3. Enrich (Speeds & Times)
        graph = enrich_graph_data(graph)

        # 4. Create a Projected Version (for stats/meters) but keep original for saving
        logger.info("📐 Projecting graph for accurate calculations...")
        graph_proj = ox.project_graph(graph)
        
        # 5. Statistics
        print_statistics(graph, graph_proj)

        # 6. Visualization
        save_visualization(graph_proj, place_name, output_dir)

        # 7. Save
        logger.info(f"💾 Saving GraphML to {output_file}...")
        ox.save_graphml(graph, filepath=output_file)
        logger.info("✅ COMPLETE: Pipeline finished successfully.")

    except Exception as e:
        logger.critical(f"❌ CRITICAL FAILURE: {e}", exc_info=True)

if __name__ == "__main__":
    # Argument Parsing
    parser = argparse.ArgumentParser(description="Download comprehensive OSM road networks.")
    
    parser.add_argument(
        "--place", 
        type=str, 
        default="Marikina City, Philippines", 
        help="Name of the place to download (default: 'Marikina City, Philippines')"
    )
    parser.add_argument(
        "--output", 
        type=str, 
        default="marikina_graph.graphml", 
        help="Path to save the GraphML file (default: 'marikina_graph.graphml')"
    )
    parser.add_argument(
        "--simplify", 
        action="store_true", 
        help="If set, simplifies graph topology (removes interstitial nodes). Default is False."
    )

    args = parser.parse_args()
    
    download_and_save_graph(args.place, args.output, args.simplify)