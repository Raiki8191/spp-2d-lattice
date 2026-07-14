package spp;

import java.util.Optional;
import java.util.random.RandomGenerator;

/** Processes SPP requests against one mutable lattice realization. */
public final class SPPSimulator {
    private final SquareLattice lattice;
    private final int budget;
    private final ShortestPathFinder shortestPathFinder;
    private final RandomGenerator pairRandom;
    private final RandomGenerator pathRandom;
    private final EdgeRemovalObserver edgeRemovalObserver;
    private long step;
    private long acceptedRequests;
    private long rejectedRequests;

    public SPPSimulator(
            SquareLattice lattice,
            int budget,
            RandomGenerator pairRandom,
            RandomGenerator pathRandom) {
        this(lattice, budget, pairRandom, pathRandom, EdgeRemovalObserver.NONE);
    }

    public SPPSimulator(
            SquareLattice lattice,
            int budget,
            RandomGenerator pairRandom,
            RandomGenerator pathRandom,
            EdgeRemovalObserver edgeRemovalObserver) {
        if (lattice == null) {
            throw new IllegalArgumentException("lattice must not be null");
        }
        if (budget < 1) {
            throw new IllegalArgumentException("budget must be at least 1");
        }
        if (pairRandom == null) {
            throw new IllegalArgumentException("pairRandom must not be null");
        }
        if (pathRandom == null) {
            throw new IllegalArgumentException("pathRandom must not be null");
        }
        if (edgeRemovalObserver == null) {
            throw new IllegalArgumentException("edgeRemovalObserver must not be null");
        }
        if (lattice.vertexCount() < 2) {
            throw new IllegalArgumentException("request processing requires at least two vertices");
        }

        this.lattice = lattice;
        this.budget = budget;
        this.shortestPathFinder = new ShortestPathFinder(lattice);
        this.pairRandom = pairRandom;
        this.pathRandom = pathRandom;
        this.edgeRemovalObserver = edgeRemovalObserver;
    }

    /** Selects an ordered pair of distinct vertices uniformly and processes its request. */
    public SPPStepResult step() {
        int vertexCount = lattice.vertexCount();
        int source = pairRandom.nextInt(vertexCount);
        int compactTarget = pairRandom.nextInt(vertexCount - 1);
        int target = compactTarget >= source ? compactTarget + 1 : compactTarget;
        return processRequest(source, target);
    }

    /** Processes one request without consuming the vertex-pair random stream. */
    public SPPStepResult processRequest(int source, int target) {
        validateRequest(source, target);
        if (step == Long.MAX_VALUE) {
            throw new IllegalStateException("step counter is exhausted");
        }

        int removedBefore = lattice.removedEdgeCount();
        int remainingBefore = lattice.remainingEdgeCount();
        Optional<ShortestPathResult> path =
                shortestPathFinder.find(source, target, budget, pathRandom);

        long nextStep = step + 1;
        if (path.isEmpty()) {
            if (lattice.removedEdgeCount() != removedBefore
                    || lattice.remainingEdgeCount() != remainingBefore) {
                throw new IllegalStateException("rejected request changed lattice edge state");
            }
            step = nextStep;
            rejectedRequests++;
            return new SPPStepResult(
                    step,
                    source,
                    target,
                    false,
                    -1,
                    0,
                    acceptedRequests,
                    rejectedRequests);
        }

        ShortestPathResult shortestPath = path.orElseThrow();
        int[] edgeIds = shortestPath.edgeIds();
        for (int edgeId : edgeIds) {
            if (!lattice.isEdgeActive(edgeId)) {
                throw new IllegalStateException("shortest path contains an inactive edge: " + edgeId);
            }
        }

        int actuallyRemoved = 0;
        for (int edgeId : edgeIds) {
            if (lattice.removeEdge(edgeId)) {
                actuallyRemoved++;
            }
        }
        if (actuallyRemoved != shortestPath.distance()) {
            throw new IllegalStateException(
                    "removed edge count does not match selected path length");
        }
        if (lattice.removedEdgeCount() - removedBefore != actuallyRemoved
                || remainingBefore - lattice.remainingEdgeCount() != actuallyRemoved) {
            throw new IllegalStateException("lattice edge counters are inconsistent");
        }

        step = nextStep;
        acceptedRequests++;
        edgeRemovalObserver.edgesRemoved(step, source, target, shortestPath);
        return new SPPStepResult(
                step,
                source,
                target,
                true,
                shortestPath.distance(),
                actuallyRemoved,
                acceptedRequests,
                rejectedRequests);
    }

    public long getStep() {
        return step;
    }

    public long getAcceptedRequests() {
        return acceptedRequests;
    }

    public long getRejectedRequests() {
        return rejectedRequests;
    }

    private void validateRequest(int source, int target) {
        int vertexCount = lattice.vertexCount();
        if (source < 0 || source >= vertexCount) {
            throw new IllegalArgumentException("source out of range: " + source);
        }
        if (target < 0 || target >= vertexCount) {
            throw new IllegalArgumentException("target out of range: " + target);
        }
        if (source == target) {
            throw new IllegalArgumentException("source and target must be different");
        }
    }
}
