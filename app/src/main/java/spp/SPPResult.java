package spp;

/** Immutable snapshot of one SPP measurement point. */
public record SPPResult(
        int run,
        int L,
        int C,
        long step,
        long removedEdges,
        long remainingEdges,
        double removedEdgeFraction,
        int largestClusterSize,
        double largestClusterFraction,
        int secondLargestClusterSize,
        double meanClusterSize,
        long acceptedRequests,
        long rejectedRequests,
        long seed) {

    public SPPResult {
        if (run < 0) {
            throw new IllegalArgumentException("run must be non-negative");
        }
        if (L < 1) {
            throw new IllegalArgumentException("L must be at least 1");
        }
        if (C < 1) {
            throw new IllegalArgumentException("C must be at least 1");
        }
        if (step < 0 || acceptedRequests < 0 || rejectedRequests < 0) {
            throw new IllegalArgumentException("steps and request counts must be non-negative");
        }

        long requestCount;
        try {
            requestCount = Math.addExact(acceptedRequests, rejectedRequests);
        } catch (ArithmeticException exception) {
            throw new IllegalArgumentException("request counter sum overflows long", exception);
        }
        if (requestCount != step) {
            throw new IllegalArgumentException(
                    "acceptedRequests + rejectedRequests must equal step");
        }

        long vertexCount = checkedVertexCount(L);
        long initialEdgeCount = checkedInitialEdgeCount(L);
        if (removedEdges < 0 || removedEdges > initialEdgeCount) {
            throw new IllegalArgumentException("removedEdges is outside the initial edge range");
        }
        if (remainingEdges != initialEdgeCount - removedEdges) {
            throw new IllegalArgumentException(
                    "remainingEdges must equal initialEdgeCount - removedEdges");
        }

        double expectedRemovedFraction =
                initialEdgeCount == 0 ? 0.0 : (double) removedEdges / initialEdgeCount;
        requireExactFraction(
                removedEdgeFraction, expectedRemovedFraction, "removedEdgeFraction");

        if (largestClusterSize < 1 || largestClusterSize > vertexCount) {
            throw new IllegalArgumentException("largestClusterSize is outside the vertex range");
        }
        if (secondLargestClusterSize < 0
                || secondLargestClusterSize > largestClusterSize) {
            throw new IllegalArgumentException(
                    "secondLargestClusterSize must be between zero and largestClusterSize");
        }
        if (!Double.isFinite(meanClusterSize) || meanClusterSize < 0.0) {
            throw new IllegalArgumentException("meanClusterSize must be finite and non-negative");
        }

        double expectedLargestFraction = (double) largestClusterSize / vertexCount;
        requireExactFraction(
                largestClusterFraction, expectedLargestFraction, "largestClusterFraction");
    }

    /** Captures a mutually consistent snapshot from the current simulation state. */
    public static SPPResult capture(
            int run,
            int L,
            int C,
            long seed,
            SquareLattice lattice,
            SPPSimulator simulator,
            ClusterStats clusterStats) {
        if (lattice == null) {
            throw new IllegalArgumentException("lattice must not be null");
        }
        if (simulator == null) {
            throw new IllegalArgumentException("simulator must not be null");
        }
        if (clusterStats == null) {
            throw new IllegalArgumentException("clusterStats must not be null");
        }
        if (L != lattice.sideLength()) {
            throw new IllegalArgumentException("L does not match the lattice side length");
        }

        long componentVertexCount = 0L;
        for (int componentSize : clusterStats.componentSizes()) {
            componentVertexCount += componentSize;
        }
        if (componentVertexCount != lattice.vertexCount()) {
            throw new IllegalArgumentException(
                    "cluster component sizes do not cover all lattice vertices");
        }

        long step = simulator.getStep();
        long acceptedRequests = simulator.getAcceptedRequests();
        long rejectedRequests = simulator.getRejectedRequests();
        long requestCount;
        try {
            requestCount = Math.addExact(acceptedRequests, rejectedRequests);
        } catch (ArithmeticException exception) {
            throw new IllegalArgumentException("simulator request counter sum overflows long", exception);
        }
        if (requestCount != step) {
            throw new IllegalArgumentException("simulator request counters are inconsistent");
        }

        long removedEdges = lattice.removedEdgeCount();
        long remainingEdges = lattice.remainingEdgeCount();
        long initialEdgeCount = lattice.initialEdgeCount();
        if (removedEdges + remainingEdges != initialEdgeCount) {
            throw new IllegalArgumentException("lattice edge counters are inconsistent");
        }

        double removedEdgeFraction =
                initialEdgeCount == 0 ? 0.0 : (double) removedEdges / initialEdgeCount;
        double largestClusterFraction =
                (double) clusterStats.largestClusterSize() / lattice.vertexCount();

        return new SPPResult(
                run,
                L,
                C,
                step,
                removedEdges,
                remainingEdges,
                removedEdgeFraction,
                clusterStats.largestClusterSize(),
                largestClusterFraction,
                clusterStats.secondLargestClusterSize(),
                clusterStats.meanClusterSize(),
                acceptedRequests,
                rejectedRequests,
                seed);
    }

    private static long checkedVertexCount(int sideLength) {
        long vertexCount = (long) sideLength * sideLength;
        if (vertexCount > Integer.MAX_VALUE) {
            throw new IllegalArgumentException("L is too large: vertex count exceeds int range");
        }
        return vertexCount;
    }

    private static long checkedInitialEdgeCount(int sideLength) {
        long initialEdgeCount = 2L * sideLength * (sideLength - 1L);
        if (initialEdgeCount > Integer.MAX_VALUE) {
            throw new IllegalArgumentException("L is too large: edge count exceeds int range");
        }
        return initialEdgeCount;
    }

    private static void requireExactFraction(double actual, double expected, String name) {
        if (!Double.isFinite(actual) || actual < 0.0 || actual > 1.0) {
            throw new IllegalArgumentException(name + " must be finite and between zero and one");
        }
        if (Double.compare(actual, expected) != 0) {
            throw new IllegalArgumentException(name + " is inconsistent with its source values");
        }
    }
}
