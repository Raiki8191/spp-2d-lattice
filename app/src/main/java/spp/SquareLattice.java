package spp;

import java.util.Arrays;

/**
 * Mutable edge state on an immutable {@code L x L} open square lattice.
 *
 * <p>Edge IDs are deterministic and contiguous. Horizontal edges receive IDs first in row-major
 * order: {@code (row, column) -- (row, column + 1)}. Vertical edges follow in row-major order:
 * {@code (row, column) -- (row + 1, column)}. Both endpoints refer to the same undirected edge ID.
 */
public final class SquareLattice {
    private static final int MAX_DEGREE = 4;

    private final int sideLength;
    private final int vertexCount;
    private final int initialEdgeCount;
    private final byte[] degrees;
    private final int[] neighbors;
    private final int[] adjacentEdgeIds;
    private final boolean[] activeEdge;
    private int removedEdgeCount;

    public SquareLattice(int sideLength) {
        if (sideLength < 1) {
            throw new IllegalArgumentException("sideLength must be at least 1");
        }

        long vertexCountLong = (long) sideLength * sideLength;
        long initialEdgeCountLong = 2L * sideLength * (sideLength - 1L);
        if (vertexCountLong > Integer.MAX_VALUE) {
            throw new IllegalArgumentException("sideLength is too large: vertex count exceeds int range");
        }
        if (initialEdgeCountLong > Integer.MAX_VALUE) {
            throw new IllegalArgumentException("sideLength is too large: edge count exceeds int range");
        }
        long adjacencySlotCountLong = vertexCountLong * MAX_DEGREE;
        if (adjacencySlotCountLong > Integer.MAX_VALUE) {
            throw new IllegalArgumentException("sideLength is too large: adjacency storage exceeds int range");
        }

        this.sideLength = sideLength;
        this.vertexCount = (int) vertexCountLong;
        this.initialEdgeCount = (int) initialEdgeCountLong;
        this.degrees = new byte[vertexCount];
        this.neighbors = new int[(int) adjacencySlotCountLong];
        this.adjacentEdgeIds = new int[(int) adjacencySlotCountLong];
        this.activeEdge = new boolean[initialEdgeCount];

        buildAdjacency();
        resetEdges();
    }

    private void buildAdjacency() {
        int edgeId = 0;

        for (int row = 0; row < sideLength; row++) {
            for (int column = 0; column < sideLength - 1; column++) {
                int left = vertexIdUnchecked(row, column);
                int right = vertexIdUnchecked(row, column + 1);
                addAdjacency(left, right, edgeId);
                addAdjacency(right, left, edgeId);
                edgeId++;
            }
        }

        for (int row = 0; row < sideLength - 1; row++) {
            for (int column = 0; column < sideLength; column++) {
                int top = vertexIdUnchecked(row, column);
                int bottom = vertexIdUnchecked(row + 1, column);
                addAdjacency(top, bottom, edgeId);
                addAdjacency(bottom, top, edgeId);
                edgeId++;
            }
        }

        if (edgeId != initialEdgeCount) {
            throw new IllegalStateException("constructed edge count does not match expected edge count");
        }
    }

    private void addAdjacency(int vertexId, int neighborId, int edgeId) {
        int neighborIndex = Byte.toUnsignedInt(degrees[vertexId]);
        if (neighborIndex >= MAX_DEGREE) {
            throw new IllegalStateException("square lattice degree exceeds " + MAX_DEGREE);
        }
        int slot = slot(vertexId, neighborIndex);
        neighbors[slot] = neighborId;
        adjacentEdgeIds[slot] = edgeId;
        degrees[vertexId]++;
    }

    public int sideLength() {
        return sideLength;
    }

    public int vertexCount() {
        return vertexCount;
    }

    public int initialEdgeCount() {
        return initialEdgeCount;
    }

    public int remainingEdgeCount() {
        return initialEdgeCount - removedEdgeCount;
    }

    public int removedEdgeCount() {
        return removedEdgeCount;
    }

    public int vertexId(int row, int column) {
        requireCoordinate(row, column);
        return vertexIdUnchecked(row, column);
    }

    public int rowOf(int vertexId) {
        requireVertexId(vertexId);
        return vertexId / sideLength;
    }

    public int columnOf(int vertexId) {
        requireVertexId(vertexId);
        return vertexId % sideLength;
    }

    public int degree(int vertexId) {
        requireVertexId(vertexId);
        return Byte.toUnsignedInt(degrees[vertexId]);
    }

    public int neighbor(int vertexId, int neighborIndex) {
        requireNeighborIndex(vertexId, neighborIndex);
        return neighbors[slot(vertexId, neighborIndex)];
    }

    public int edgeId(int vertexId, int neighborIndex) {
        requireNeighborIndex(vertexId, neighborIndex);
        return adjacentEdgeIds[slot(vertexId, neighborIndex)];
    }

    public boolean isEdgeActive(int edgeId) {
        requireEdgeId(edgeId);
        return activeEdge[edgeId];
    }

    /**
     * Removes an edge if it is active.
     *
     * @return {@code true} if this call changed the edge state, otherwise {@code false}
     */
    public boolean removeEdge(int edgeId) {
        requireEdgeId(edgeId);
        if (!activeEdge[edgeId]) {
            return false;
        }
        activeEdge[edgeId] = false;
        removedEdgeCount++;
        return true;
    }

    public void resetEdges() {
        Arrays.fill(activeEdge, true);
        removedEdgeCount = 0;
    }

    private int vertexIdUnchecked(int row, int column) {
        return row * sideLength + column;
    }

    private static int slot(int vertexId, int neighborIndex) {
        return vertexId * MAX_DEGREE + neighborIndex;
    }

    private void requireCoordinate(int row, int column) {
        if (row < 0 || row >= sideLength || column < 0 || column >= sideLength) {
            throw new IllegalArgumentException(
                    "coordinate out of range: (" + row + ", " + column + ")");
        }
    }

    private void requireVertexId(int vertexId) {
        if (vertexId < 0 || vertexId >= vertexCount) {
            throw new IllegalArgumentException("vertexId out of range: " + vertexId);
        }
    }

    private void requireNeighborIndex(int vertexId, int neighborIndex) {
        requireVertexId(vertexId);
        int degree = Byte.toUnsignedInt(degrees[vertexId]);
        if (neighborIndex < 0 || neighborIndex >= degree) {
            throw new IllegalArgumentException(
                    "neighborIndex out of range for vertex " + vertexId + ": " + neighborIndex);
        }
    }

    private void requireEdgeId(int edgeId) {
        if (edgeId < 0 || edgeId >= initialEdgeCount) {
            throw new IllegalArgumentException("edgeId out of range: " + edgeId);
        }
    }
}
