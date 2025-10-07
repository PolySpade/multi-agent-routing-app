# filename: masfro-backend/download_map.py
import osmnx as ox

def download_and_save_graph():
    """
    Downloads the Marikina City graph with simplification disabled to prevent
    the graph from being erroneously deleted.
    """
    place_name = "Marikina City, Philippines"
    filepath = "marikina_graph.graphml"
    print(f"--- Attempting to download map data for {place_name} ---")

    try:
        ox.settings.user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.36"
        ox.settings.log_console = True

        gdf = ox.geocode_to_gdf(place_name)

        # FIX 1: Use union_all() to address the deprecation warning.
        polygon = gdf.union_all()

        # FIX 2: The key fix is simplify=False, which prevents the graph from being destroyed.
        graph = ox.graph_from_polygon(polygon, network_type='drive', simplify=False)

        if graph.number_of_edges() > 0:
            ox.save_graphml(graph, filepath=filepath)
            print(f"\n✅ SUCCESS: Graph downloaded and saved successfully to '{filepath}'")
            print(f"   The graph has {graph.number_of_nodes()} nodes and {graph.number_of_edges()} edges.")
        else:
            print("\n❌ FAILURE: Download resulted in an empty graph. File not saved.")

    except Exception as e:
        print(f"\n❌ CRITICAL FAILURE: An error occurred during download: {e}")

if __name__ == "__main__":
    download_and_save_graph()