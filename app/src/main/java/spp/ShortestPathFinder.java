package spp;

import java.math.BigInteger;
import java.util.Arrays;
import java.util.Optional;
import java.util.random.RandomGenerator;

/**
 * Finds a uniformly selected shortest path on the currently active lattice edges.
 *
 * <p>This class reuses its BFS work arrays and is not thread-safe. The lattice edge state is read
 * during a search but is never modified.
 */
public final class ShortestPathFinder {
    private static final BigInteger ONE = BigInteger.ONE;

    private final SquareLattice lattice;
    private final int[] distances;
    private final BigInteger[] pathCounts;
    private final int[] queue;
    private final int[] touchedVertices;
    private int touchedCount;
    private byte[] randomBytes = new byte[0];

    public ShortestPathFinder(SquareLattice lattice) {
        if (lattice == null) {
            throw new IllegalArgumentException("lattice must not be null");
        }
        this.lattice = lattice;
        int vertexCount = lattice.vertexCount();
        this.distances = new int[vertexCount];
        Arrays.fill(distances, -1);
        this.pathCounts = new BigInteger[vertexCount];
        this.queue = new int[vertexCount];
        this.touchedVertices = new int[vertexCount];
    }

    /**
     * Searches active edges up to {@code budget} and returns one uniformly selected shortest path.
     */
    public Optional<ShortestPathResult> find(
            int source, int target, int budget, RandomGenerator randomGenerator) {
        validateInputs(source, target, budget, randomGenerator);
        clearPreviousSearch();

        int targetDistance = runBfs(source, target, budget);
        if (targetDistance < 0) {
            return Optional.empty();
        }

        int[] edgeIds = selectPath(source, target, targetDistance, randomGenerator);
        return Optional.of(new ShortestPathResult(targetDistance, edgeIds));
    }

    private int runBfs(int source, int target, int budget) {
        int head = 0;
        int tail = 0;
        int targetDistance = -1;

        distances[source] = 0;
        pathCounts[source] = ONE;
        touchedVertices[touchedCount++] = source;
        queue[tail++] = source;

        while (head < tail) {
            int vertex = queue[head++];
            int distance = distances[vertex];

            // Queue order is non-decreasing in distance. All distance Q - 1 vertices have now
            // contributed before the first distance Q vertex reaches the head of the queue.
            if (targetDistance >= 0 && distance >= targetDistance) {
                break;
            }
            if (distance >= budget) {
                continue;
            }

            int nextDistance = distance + 1;
            for (int i = 0; i < lattice.degree(vertex); i++) {
                int edgeId = lattice.edgeId(vertex, i);
                if (!lattice.isEdgeActive(edgeId)) {
                    continue;
                }

                int neighbor = lattice.neighbor(vertex, i);
                if (distances[neighbor] < 0) {
                    distances[neighbor] = nextDistance;
                    pathCounts[neighbor] = pathCounts[vertex];
                    touchedVertices[touchedCount++] = neighbor;
                    queue[tail++] = neighbor;
                } else if (distances[neighbor] == nextDistance) {
                    pathCounts[neighbor] = pathCounts[neighbor].add(pathCounts[vertex]);
                }

                if (neighbor == target && targetDistance < 0) {
                    targetDistance = nextDistance;
                }
            }
        }

        return targetDistance;
    }

    private int[] selectPath(
            int source,
            int target,
            int targetDistance,
            RandomGenerator randomGenerator) {
        int[] edgeIds = new int[targetDistance];
        int current = target;

        for (int pathIndex = targetDistance - 1; pathIndex >= 0; pathIndex--) {
            int predecessorDistance = distances[current] - 1;
            BigInteger totalWeight = BigInteger.ZERO;

            for (int i = 0; i < lattice.degree(current); i++) {
                int edgeId = lattice.edgeId(current, i);
                int neighbor = lattice.neighbor(current, i);
                if (lattice.isEdgeActive(edgeId) && distances[neighbor] == predecessorDistance) {
                    totalWeight = totalWeight.add(pathCounts[neighbor]);
                }
            }

            BigInteger draw = randomBelow(totalWeight, randomGenerator);
            int selectedPredecessor = -1;
            int selectedEdgeId = -1;
            for (int i = 0; i < lattice.degree(current); i++) {
                int edgeId = lattice.edgeId(current, i);
                int neighbor = lattice.neighbor(current, i);
                if (!lattice.isEdgeActive(edgeId) || distances[neighbor] != predecessorDistance) {
                    continue;
                }

                BigInteger weight = pathCounts[neighbor];
                if (draw.compareTo(weight) < 0) {
                    selectedPredecessor = neighbor;
                    selectedEdgeId = edgeId;
                    break;
                }
                draw = draw.subtract(weight);
            }

            if (selectedPredecessor < 0) {
                throw new IllegalStateException("failed to select a shortest-path predecessor");
            }
            edgeIds[pathIndex] = selectedEdgeId;
            current = selectedPredecessor;
        }

        if (current != source) {
            throw new IllegalStateException("selected path does not end at source");
        }
        return edgeIds;
    }

    /** Returns a uniform integer in {@code [0, upperBound)} using rejection sampling. */
    private BigInteger randomBelow(BigInteger upperBound, RandomGenerator randomGenerator) {
        if (upperBound.signum() <= 0) {
            throw new IllegalStateException("shortest-path weight must be positive");
        }

        int bitLength = upperBound.bitLength();
        int byteLength = (bitLength + 7) / 8;
        if (randomBytes.length < byteLength) {
            randomBytes = new byte[byteLength];
        }

        int leadingUnusedBytes = randomBytes.length - byteLength;
        int excessBits = byteLength * 8 - bitLength;
        BigInteger candidate;
        do {
            randomGenerator.nextBytes(randomBytes);
            Arrays.fill(randomBytes, 0, leadingUnusedBytes, (byte) 0);
            randomBytes[leadingUnusedBytes] &= (byte) (0xff >>> excessBits);
            candidate = new BigInteger(1, randomBytes);
        } while (candidate.compareTo(upperBound) >= 0);
        return candidate;
    }

    private void clearPreviousSearch() {
        for (int i = 0; i < touchedCount; i++) {
            int vertex = touchedVertices[i];
            distances[vertex] = -1;
            pathCounts[vertex] = null;
        }
        touchedCount = 0;
    }

    private void validateInputs(
            int source, int target, int budget, RandomGenerator randomGenerator) {
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
        if (budget < 1) {
            throw new IllegalArgumentException("budget must be at least 1");
        }
        if (randomGenerator == null) {
            throw new IllegalArgumentException("randomGenerator must not be null");
        }
    }
}
