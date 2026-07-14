"""Union-Find statistics used to reconstruct square-lattice deletion states."""

from __future__ import annotations


class UnionFind:
    """Disjoint sets with component sizes, largest size, and squared-size sum."""

    def __init__(self, vertex_count: int) -> None:
        if vertex_count < 1:
            raise ValueError("vertex_count must be positive")
        self.parent = list(range(vertex_count))
        self.size = [1] * vertex_count
        self.largest_size = 1
        self.sum_size_squared = vertex_count

    def find(self, vertex: int) -> int:
        root = vertex
        while self.parent[root] != root:
            root = self.parent[root]
        while self.parent[vertex] != vertex:
            next_vertex = self.parent[vertex]
            self.parent[vertex] = root
            vertex = next_vertex
        return root

    def union(self, first: int, second: int) -> bool:
        first_root = self.find(first)
        second_root = self.find(second)
        if first_root == second_root:
            return False
        if self.size[first_root] < self.size[second_root]:
            first_root, second_root = second_root, first_root
        first_size = self.size[first_root]
        second_size = self.size[second_root]
        self.parent[second_root] = first_root
        self.size[first_root] = first_size + second_size
        self.sum_size_squared += 2 * first_size * second_size
        self.largest_size = max(self.largest_size, self.size[first_root])
        return True

    def mean_finite_cluster_size(self) -> float:
        vertex_count = len(self.parent)
        denominator = vertex_count - self.largest_size
        if denominator == 0:
            return 0.0
        numerator = self.sum_size_squared - self.largest_size**2
        return numerator / denominator
