"""
Implementation of Dijkstra's algorithm for shortest path finding.

This module provides functions to calculate the shortest path between locations
using Dijkstra's algorithm.
"""
import heapq
from typing import Dict, List, Tuple, Set, Optional, Union
import logging

# Set up logging
logger = logging.getLogger(__name__)


class DijkstraPathFinder:
    """
    Implementation of Dijkstra's algorithm for shortest path finding.
    """

    def __init__(self):
        """Initialize the Dijkstra path finder."""
        pass

    @staticmethod
    def calculate_shortest_path(
        graph: Dict[str, Dict[str, float]],
        start: str,
        end: str
    ) -> Tuple[Optional[List[str]], Optional[float]]:
        """
        Calculate the shortest path between two nodes using Dijkstra's algorithm.

        Args:
            graph: A dictionary of dictionaries representing the graph.
                  Format: {node1: {node2: distance, node3: distance, ...}, ...}
            start: Starting node.
            end: Target node.

        Returns:
            A tuple containing:
            - List of nodes representing the shortest path (or None if no path exists)
            - Total distance of the path (or None if no path exists)
        """
        if start not in graph or end not in graph:
            logger.warning(f"Start node '{start}' or end node '{end}' not in graph")
            return None, None

        # Priority queue: (distance, node, path)
        queue = [(0, start, [start])]
        visited: Set[str] = set()

        while queue:
            (dist, current, path) = heapq.heappop(queue)
            
            if current in visited:
                continue

            visited.add(current)
            
            if current == end:
                return path, dist
            
            # Explore neighbors
            for neighbor, distance in graph[current].items():
                if neighbor not in visited:
                    new_dist = dist + distance
                    new_path = path + [neighbor]
                    heapq.heappush(queue, (new_dist, neighbor, new_path))
        
        logger.warning(f"No path found from '{start}' to '{end}'")
        return None, None

    @staticmethod
    def calculate_all_shortest_paths(
        graph: Dict[str, Dict[str, float]],
        nodes: List[str]
    ) -> Dict[str, Dict[str, Dict[str, Union[List[str], float]]]]:
        """
        Calculate shortest paths between all pairs of nodes.

        Args:
            graph: A dictionary of dictionaries representing the graph.
            nodes: List of nodes to calculate paths between.

        Returns:
            Dictionary with format:
            {
                start_node: {
                    end_node: {
                        'path': [node1, node2, ...],
                        'distance': total_distance
                    }
                }
            }
        """
        result = {}
        
        for start_node in nodes:
            result[start_node] = {}
            
            for end_node in nodes:
                if start_node == end_node:
                    result[start_node][end_node] = {
                        'path': [start_node],
                        'distance': 0
                    }
                    continue
                
                path, distance = DijkstraPathFinder.calculate_shortest_path(
                    graph, start_node, end_node
                )
                
                if path and distance is not None:
                    result[start_node][end_node] = {
                        'path': path,
                        'distance': distance
                    }
                else:
                    result[start_node][end_node] = {
                        'path': None,
                        'distance': float('inf')
                    }
        
        return result