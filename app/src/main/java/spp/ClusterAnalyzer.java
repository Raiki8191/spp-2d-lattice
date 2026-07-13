package spp;

import java.util.Arrays;

/** Measures connected components using only the currently active lattice edges. */
public final class ClusterAnalyzer {
    private boolean[] visited = new boolean[0];
    private int[] queue = new int[0];
    private int[] componentSizeWorkspace = new int[0];

    public ClusterStats analyze(SquareLattice lattice) {
        if (lattice == null) {
            throw new IllegalArgumentException("lattice must not be null");
        }

        int vertexCount = lattice.vertexCount();
        ensureCapacity(vertexCount);
        Arrays.fill(visited, 0, vertexCount, false);

        int componentCount = 0;
        for (int start = 0; start < vertexCount; start++) {
            if (visited[start]) {
                continue;
            }
            componentSizeWorkspace[componentCount++] = breadthFirstComponentSize(lattice, start);
        }

        int[] componentSizes = Arrays.copyOf(componentSizeWorkspace, componentCount);
        Arrays.sort(componentSizes);
        reverse(componentSizes);

        int largest = componentSizes[0];
        int secondLargest = componentCount == 1 ? 0 : componentSizes[1];
        double mean = ClusterStats.calculateMeanClusterSize(componentSizes);
        return new ClusterStats(componentCount, largest, secondLargest, mean, componentSizes);
    }

    private int breadthFirstComponentSize(SquareLattice lattice, int start) {
        int head = 0;
        int tail = 0;
        queue[tail++] = start;
        visited[start] = true;

        while (head < tail) {
            int vertex = queue[head++];
            int degree = lattice.degree(vertex);
            for (int neighborIndex = 0; neighborIndex < degree; neighborIndex++) {
                int edgeId = lattice.edgeId(vertex, neighborIndex);
                if (!lattice.isEdgeActive(edgeId)) {
                    continue;
                }

                int neighbor = lattice.neighbor(vertex, neighborIndex);
                if (!visited[neighbor]) {
                    visited[neighbor] = true;
                    queue[tail++] = neighbor;
                }
            }
        }
        return tail;
    }

    private void ensureCapacity(int vertexCount) {
        if (visited.length >= vertexCount) {
            return;
        }
        visited = new boolean[vertexCount];
        queue = new int[vertexCount];
        componentSizeWorkspace = new int[vertexCount];
    }

    private static void reverse(int[] values) {
        for (int left = 0, right = values.length - 1; left < right; left++, right--) {
            int temporary = values[left];
            values[left] = values[right];
            values[right] = temporary;
        }
    }
}
