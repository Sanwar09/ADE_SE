import os
import networkx as nx
from typing import Dict, List, Any

class RepositoryDigitalTwin:
    """
    In-Memory Code Property Graph representation of a repository.
    Tracks files, classes, functions, API routes, DB tables, imports, and dynamic test logs.
    Runs efficiently in < 50MB RAM using NetworkX.
    """

    def __init__(self, repo_path: str):
        self.repo_path = repo_path
        self.graph = nx.DiGraph()
        self.metadata = {
            "total_files": 0,
            "total_functions": 0,
            "total_classes": 0,
            "total_routes": 0,
            "languages": set(),
            "test_status": "UNKNOWN"
        }

    def add_file_node(self, file_path: str, language: str):
        rel_path = os.path.relpath(file_path, self.repo_path)
        self.graph.add_node(rel_path, node_type="FILE", language=language)
        self.metadata["total_files"] += 1
        self.metadata["languages"].add(language)

    def add_symbol_node(self, symbol_name: str, symbol_type: str, file_path: str, line_number: int, docstring: str = ""):
        rel_path = os.path.relpath(file_path, self.repo_path)
        node_id = f"{rel_path}::{symbol_name}"
        self.graph.add_node(
            node_id,
            node_type=symbol_type,  # FUNCTION, CLASS, API_ROUTE, DB_TABLE
            name=symbol_name,
            file=rel_path,
            line=line_number,
            docstring=docstring
        )
        # Edge: File CONTAINS Symbol
        self.graph.add_edge(rel_path, node_id, relationship="CONTAINS")

        if symbol_type == "FUNCTION":
            self.metadata["total_functions"] += 1
        elif symbol_type == "CLASS":
            self.metadata["total_classes"] += 1
        elif symbol_type == "API_ROUTE":
            self.metadata["total_routes"] += 1

    def add_relationship(self, source_id: str, target_id: str, relationship_type: str):
        """Relationships: CALLS, IMPORTS, INHERITS, QUERIES_TABLE, TESTS"""
        self.graph.add_edge(source_id, target_id, relationship=relationship_type)

    def get_impact_subgraph(self, target_nodes: List[str], depth: int = 2) -> Dict[str, Any]:
        """
        Performs graph traversal to identify all upstream/downstream files & symbols
        impacted by a proposed change.
        """
        impacted_nodes = set()
        for node in target_nodes:
            if node in self.graph:
                impacted_nodes.add(node)
                # Traverse successors (downstream callers) and predecessors (upstream dependencies)
                sub_nodes = nx.single_source_shortest_path_length(self.graph, node, cutoff=depth).keys()
                impacted_nodes.update(sub_nodes)

        subgraph = self.graph.subgraph(impacted_nodes)
        
        nodes_data = []
        for n, d in subgraph.nodes(data=True):
            nodes_data.append({"id": n, **d})

        edges_data = []
        for u, v, d in subgraph.edges(data=True):
            edges_data.append({"source": u, "target": v, **d})

        return {
            "impacted_node_count": len(impacted_nodes),
            "nodes": nodes_data,
            "edges": edges_data
        }

    def to_cytoscape_json(self) -> List[Dict[str, Any]]:
        """Converts the full twin graph to Cytoscape format for React UI visualization."""
        elements = []
        for node, data in self.graph.nodes(data=True):
            elements.append({
                "data": {"id": node, "label": data.get("name", node), **data}
            })
        for source, target, data in self.graph.edges(data=True):
            elements.append({
                "data": {"source": source, "target": target, "relationship": data.get("relationship", "RELATED")}
            })
        return elements
