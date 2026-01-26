# filename: app/environment/graph_manager.py
import osmnx as ox
import networkx as nx
import os # Import the os module to check for file existence
from pathlib import Path
from threading import Lock
import logging

logger = logging.getLogger(__name__)


class DynamicGraphEnvironment:
    """
    Manages the road network graph for the simulation by loading it
    from a local .graphml file.

    Thread-safe implementation using a lock to prevent race conditions
    during graph updates.
    """
    def __init__(self):
        base = Path(__file__).resolve().parent   # .../app/environment
        # If data folder is at mesfro-backend/data use parent.parent
        candidate = (base.parent.parent / "data" / "marikina_graph.graphml").resolve()
        # fallback: app/data (one-level up) if you actually have app/data
        if not candidate.exists():
            candidate = (base.parent / "data" / "marikina_graph.graphml").resolve()
        self.filepath = str(candidate)
        # print(f"Graph file path set to: {self.filepath}")
        self.graph = None

        # Thread safety
        self._lock = Lock()
        self._is_updating = False

        self._load_graph_from_file()

    def _load_graph_from_file(self):
        """
        Loads the graph from a local file and pre-processes it.
        """
        print(f"--- Attempting to load graph from local file: {self.filepath} ---")
        if not os.path.exists(self.filepath):
            print(f"\n❌ FAILURE: Map file not found at '{self.filepath}'.")
            print("   Please run the 'download_map.py' script first to download the map data.")
            return

        try:
            # Load the graph from the file
            self.graph = ox.load_graphml(self.filepath)
            print("Graph loaded successfully from file.")

            # --- Pre-processing Steps ---
            print("Pre-processing graph (adding/resetting risk and weight attributes)...")
            for u, v, key in self.graph.edges(keys=True):
                # Access edge data directly to ensure modifications persist
                edge_data = self.graph[u][v][key]
                edge_data['risk_score'] = 0.0  # Start with safe roads (0.0), flood data will increase risk
                if 'length' not in edge_data:
                    edge_data['length'] = 1.0 # Should exist, but good to be safe
                edge_data['weight'] = edge_data['length'] * (1.0 + edge_data['risk_score'])  # Base distance + risk penalty

            # Verify preprocessing worked
            sample_count = 0
            verified_count = 0
            for u, v, key in list(self.graph.edges(keys=True))[:5]:
                edge_data = self.graph[u][v][key]
                has_risk = 'risk_score' in edge_data
                if has_risk:
                    verified_count += 1
                sample_count += 1
                if sample_count <= 3:
                    print(f"  Sample edge ({u},{v},{key}): risk_score={'YES' if has_risk else 'MISSING'}")

            print(f"Graph pre-processing complete. Verified {verified_count}/{sample_count} sample edges have risk_score.")

        except Exception as e:
            print(f"\n❌ An error occurred while loading or processing the graph file: {e}")
            self.graph = None

    def update_edge_risk(self, u, v, key, risk_factor: float):
        """
        Update the risk score for a specific edge (thread-safe).

        Args:
            u: Source node ID
            v: Target node ID
            key: Edge key (for multigraphs)
            risk_factor: Risk score (0.0-1.0)
        """
        if self.graph is None:
            return

        with self._lock:
            self._is_updating = True
            try:
                edge_data = self.graph.edges[u, v, key]
                edge_data['risk_score'] = risk_factor
                # Base distance + risk penalty
                edge_data['weight'] = edge_data['length'] * (1.0 + risk_factor)
            except KeyError:
                logger.warning(f"Edge ({u}, {v}, {key}) not found in graph")
            finally:
                self._is_updating = False

    def batch_update_edge_risks(self, risk_updates: dict):
        """
        Batch update multiple edge risks (more efficient than individual updates).

        Args:
            risk_updates: Dict mapping (u, v, key) tuples to risk scores
                Format: {(u, v, key): risk_score, ...}

        Example:
            >>> env.batch_update_edge_risks({
            ...     (1, 2, 0): 0.5,
            ...     (2, 3, 0): 0.8
            ... })
        """
        if self.graph is None:
            return

        with self._lock:
            self._is_updating = True
            try:
                updated_count = 0
                for (u, v, key), risk_factor in risk_updates.items():
                    try:
                        edge_data = self.graph.edges[u, v, key]
                        edge_data['risk_score'] = risk_factor
                        edge_data['weight'] = edge_data['length'] * (1.0 + risk_factor)
                        updated_count += 1
                    except KeyError:
                        logger.warning(f"Edge ({u}, {v}, {key}) not found in graph")

                logger.info(f"Batch updated {updated_count}/{len(risk_updates)} edges")
            finally:
                self._is_updating = False

    def is_updating(self) -> bool:
        """
        Check if graph is currently being updated.

        Returns:
            True if update in progress, False otherwise
        """
        return self._is_updating

    def get_graph(self) -> nx.MultiDiGraph:
        """
        Get the graph instance.

        Returns:
            NetworkX MultiDiGraph instance
        """
        return self.graph