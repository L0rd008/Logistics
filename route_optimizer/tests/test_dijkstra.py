"""
Tests for Dijkstra's algorithm implementation.

This module contains tests for the DijkstraPathFinder class.
"""
import unittest
from route_optimizer.core.dijkstra import DijkstraPathFinder


class TestDijkstraPathFinder(unittest.TestCase):
    """Test cases for DijkstraPathFinder."""

    def setUp(self):
        """Set up test fixtures."""
        self.path_finder = DijkstraPathFinder()
        
        # Simple test graph
        # A -- 1 --> B -- 2 --> C
        # |           |
        # 4           3
        # |           |
        # v           v
        # D -- 5 --> E
        self.simple_graph = {
            'A': {'B': 1.0, 'D': 4.0},
            'B': {'C': 2.0, 'E': 3.0},
            'C': {},
            'D': {'E': 5.0},
            'E': {}
        }
        
        # More complex graph with cycles and different paths
        self.complex_graph = {
            'A': {'B': 1.0, 'C': 4.0},
            'B': {'C': 2.0, 'D': 5.0},
            'C': {'D': 1.0, 'E': 3.0},
            'D': {'B': 1.0, 'E': 2.0, 'F': 5.0},
            'E': {'F': 1.0},
            'F': {'A': 10.0}
        }

    def test_shortest_path_simple(self):
        """Test finding shortest path in a simple graph."""
        # Test A to C: A -> B -> C
        path, distance = self.path_finder.calculate_shortest_path(
            self.simple_graph, 'A', 'C'
        )
        self.assertEqual(path, ['A', 'B', 'C'])
        self.assertEqual(distance, 3.0)
        
        # Test A to E: A -> B -> E
        path, distance = self.path_finder.calculate_shortest_path(
            self.simple_graph, 'A', 'E'
        )
        self.assertEqual(path, ['A', 'B', 'E'])
        self.assertEqual(distance, 4.0)
        
        # Test D to C: no path exists
        path, distance = self.path_finder.calculate_shortest_path(
            self.simple_graph, 'D', 'C'
        )
        self.assertIsNone(path)
        self.assertIsNone(distance)

    def test_shortest_path_complex(self):
        """Test finding shortest path in a more complex graph."""
        # Test A to F: A -> C -> E -> F
        path, distance = self.path_finder.calculate_shortest_path(
            self.complex_graph, 'A', 'F'
        )
        self.assertEqual(path, ['A', 'C', 'E', 'F'])
        self.assertEqual(distance, 8.0)  # 4 + 3 + 1
        
        # Test D to A: D -> B -> C -> E -> F -> A
        path, distance = self.path_finder.calculate_shortest_path(
            self.complex_graph, 'D', 'A'
        )
        self.assertEqual(path, ['D', 'B', 'C', 'E', 'F', 'A'])
        self.assertEqual(distance, 15.0)  # 1 + 2 + 3 + 1 + 10

    def test_edge_cases(self):
        """Test edge cases for the shortest path algorithm."""
        # Test path from a node to itself
        path, distance = self.path_finder.calculate_shortest_path(
            self.simple_graph, 'A', 'A'
        )
        self.assertEqual(path, ['A'])
        self.assertEqual(distance, 0.0)
        
        # Test with non-existent nodes
        path, distance = self.path_finder.calculate_shortest_path(
            self.simple_graph, 'X', 'Y'
        )
        self.assertIsNone(path)
        self.assertIsNone(distance)
        
        # Test with start node exists but end doesn't
        path, distance = self.path_finder.calculate_shortest_path(
            self.simple_graph, 'A', 'Z'
        )
        self.assertIsNone(path)
        self.assertIsNone(distance)

    def test_all_shortest_paths(self):
        """Test calculating all shortest paths between nodes."""
        nodes = ['A', 'B', 'C']
        all_paths = self.path_finder.calculate_all_shortest_paths(self.simple_graph, nodes)
        
        # Verify the structure of the result
        self.assertIn('A', all_paths)
        self.assertIn('B', all_paths)
        self.assertIn('C', all_paths)
        self.assertIn('B', all_paths['A'])
        self.assertIn('C', all_paths['A'])
        
        # Check specific paths
        self.assertEqual(all_paths['A']['B']['path'], ['A', 'B'])
        self.assertEqual(all_paths['A']['B']['distance'], 1.0)
        self.assertEqual(all_paths['A']['C']['path'], ['A', 'B', 'C'])
        self.assertEqual(all_paths['A']['C']['distance'], 3.0)
        self.assertEqual(all_paths['B']['C']['path'], ['B', 'C'])
        self.assertEqual(all_paths['B']['C']['distance'], 2.0)
        
        # No path from C to A or B
        self.assertIsNone(all_paths['C']['A']['path'])
        self.assertIsNone(all_paths['C']['A']['distance'])
        self.assertIsNone(all_paths['C']['B']['path'])
        self.assertIsNone(all_paths['C']['B']['distance'])

    def test_negative_weights(self):
        """Test behavior with negative weights (not supported by standard Dijkstra)."""
        graph_with_negative = {
            'A': {'B': 1.0, 'C': 4.0},
            'B': {'C': -2.0}  # Negative weight
        }
        
        # The implementation should handle this by ignoring negative weights
        # or by returning a correct path based on the algorithm's behavior
        path, distance = self.path_finder.calculate_shortest_path(
            graph_with_negative, 'A', 'C'
        )
        # We expect either:
        # 1. A direct path from A to C with distance 4.0, or
        # 2. A path through B: A -> B -> C with distance -1.0 (if negative weights are allowed)
        # Since Dijkstra's doesn't handle negative weights correctly, we expect the first case
        self.assertEqual(path, ['A', 'C'])
        self.assertEqual(distance, 4.0)


if __name__ == '__main__':
    unittest.main()