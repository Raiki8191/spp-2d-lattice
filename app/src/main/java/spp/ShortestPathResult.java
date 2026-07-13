package spp;

/** A found shortest path represented by edge IDs in source-to-target order. */
public record ShortestPathResult(int distance, int[] edgeIds) {
    public ShortestPathResult {
        if (distance < 0) {
            throw new IllegalArgumentException("distance must be non-negative");
        }
        if (edgeIds == null) {
            throw new IllegalArgumentException("edgeIds must not be null");
        }
        if (edgeIds.length != distance) {
            throw new IllegalArgumentException("edgeIds length must equal distance");
        }
        for (int edgeId : edgeIds) {
            if (edgeId < 0) {
                throw new IllegalArgumentException("edgeIds must be non-negative");
            }
        }
        edgeIds = edgeIds.clone();
    }

    @Override
    public int[] edgeIds() {
        return edgeIds.clone();
    }
}
