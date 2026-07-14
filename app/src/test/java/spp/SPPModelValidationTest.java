package spp;

import static org.junit.jupiter.api.Assertions.assertArrayEquals;
import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertTrue;

import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.List;
import java.util.Optional;
import java.util.Random;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.io.TempDir;

/** Small-state validation of the SPP model against hand calculations and an independent graph. */
class SPPModelValidationTest {
    private static final int L2_STATE_COUNT = 16;
    private static final int L2_ORDERED_PAIR_COUNT = 12;
    private static final int L3_SAMPLED_STATE_COUNT = 24;
    private static final int L3_ORDERED_PAIR_COUNT = 72;

    @TempDir Path temporaryDirectory;

    @Test
    void edgeDeletionAndClusterStatisticsAreMonotoneAfterEveryRequest() {
        SquareLattice lattice = new SquareLattice(5);
        SPPSimulator simulator = simulator(lattice, 3, 101L, 202L);
        ClusterAnalyzer analyzer = new ClusterAnalyzer();

        int previousRemoved = lattice.removedEdgeCount();
        int previousRemaining = lattice.remainingEdgeCount();
        int previousLargest = analyzer.analyze(lattice).largestClusterSize();
        long previousAccepted = simulator.getAcceptedRequests();
        long previousRejected = simulator.getRejectedRequests();

        for (int request = 0; request < 100; request++) {
            simulator.step();
            ClusterStats stats = analyzer.analyze(lattice);

            assertTrue(lattice.removedEdgeCount() >= previousRemoved);
            assertTrue(lattice.remainingEdgeCount() <= previousRemaining);
            assertTrue(stats.largestClusterSize() <= previousLargest);
            assertTrue(simulator.getAcceptedRequests() >= previousAccepted);
            assertTrue(simulator.getRejectedRequests() >= previousRejected);
            assertEquals(
                    simulator.getStep(),
                    simulator.getAcceptedRequests() + simulator.getRejectedRequests());

            previousRemoved = lattice.removedEdgeCount();
            previousRemaining = lattice.remainingEdgeCount();
            previousLargest = stats.largestClusterSize();
            previousAccepted = simulator.getAcceptedRequests();
            previousRejected = simulator.getRejectedRequests();
        }
    }

    @Test
    void budgetOneAcceptsExactlyActiveAdjacentPairs() {
        SquareLattice adjacentLattice = new SquareLattice(3);
        SPPSimulator adjacentSimulator = simulator(adjacentLattice, 1, 1L, 2L);

        SPPStepResult accepted = adjacentSimulator.processRequest(0, 1);
        SPPStepResult repeated = adjacentSimulator.processRequest(0, 1);

        assertTrue(accepted.accepted());
        assertEquals(1, accepted.pathLength());
        assertEquals(1, accepted.removedEdgeCount());
        assertFalse(repeated.accepted());
        assertEquals(-1, repeated.pathLength());
        assertEquals(0, repeated.removedEdgeCount());

        SquareLattice nonAdjacentLattice = new SquareLattice(3);
        SPPStepResult nonAdjacent =
                simulator(nonAdjacentLattice, 1, 1L, 2L).processRequest(0, 2);
        assertFalse(nonAdjacent.accepted());
        assertEquals(0, nonAdjacentLattice.removedEdgeCount());
    }

    @Test
    void infiniteBudgetEquivalentAcceptsWithinComponentsAndRejectsAcrossComponents() {
        SquareLattice connected = new SquareLattice(3);
        ReferenceGraph connectedReference = new ReferenceGraph(3, activeState(connected));
        int expectedDistance = connectedReference.distance(0, 8, 8);

        SPPStepResult longPath = simulator(connected, 8, 3L, 4L).processRequest(0, 8);

        assertTrue(longPath.accepted());
        assertEquals(expectedDistance, longPath.pathLength());

        SquareLattice split = new SquareLattice(2);
        split.removeEdge(2);
        split.removeEdge(3);
        SPPSimulator splitSimulator = simulator(split, 3, 5L, 6L);

        SPPStepResult acrossComponents = splitSimulator.processRequest(0, 2);
        int withinDistance = new ReferenceGraph(2, activeState(split)).distance(0, 1, 3);
        SPPStepResult withinComponent = splitSimulator.processRequest(0, 1);

        assertFalse(acrossComponents.accepted());
        assertTrue(withinComponent.accepted());
        assertEquals(withinDistance, withinComponent.pathLength());
    }

    @Test
    void fixedTwoByTwoRequestSequenceMatchesHandCalculatedStates() {
        SquareLattice lattice = new SquareLattice(2);
        SPPSimulator simulator = simulator(lattice, 3, 7L, 8L);
        ClusterAnalyzer analyzer = new ClusterAnalyzer();

        assertStep(
                simulator.processRequest(0, 1), true, 1, 1, 1, 0);
        assertState(lattice, analyzer, new int[] {0}, 1, 3, new int[] {4}, 4, 0, 0.0);

        assertStep(
                simulator.processRequest(0, 3), true, 2, 2, 2, 0);
        assertState(
                lattice,
                analyzer,
                new int[] {0, 1, 2},
                3,
                1,
                new int[] {2, 1, 1},
                2,
                1,
                1.0);

        assertStep(
                simulator.processRequest(1, 3), true, 1, 1, 3, 0);
        assertState(
                lattice,
                analyzer,
                new int[] {0, 1, 2, 3},
                4,
                0,
                new int[] {1, 1, 1, 1},
                1,
                1,
                1.0);

        assertStep(
                simulator.processRequest(0, 1), false, -1, 0, 3, 1);
        assertState(
                lattice,
                analyzer,
                new int[] {0, 1, 2, 3},
                4,
                0,
                new int[] {1, 1, 1, 1},
                1,
                1,
                1.0);
    }

    @Test
    void allTwoByTwoEdgeStatesMatchIndependentReference() {
        int shortestPathComparisons = 0;
        int componentComparisons = 0;

        for (int mask = 0; mask < L2_STATE_COUNT; mask++) {
            boolean[] active = new boolean[4];
            for (int edgeId = 0; edgeId < active.length; edgeId++) {
                active[edgeId] = (mask & (1 << edgeId)) != 0;
            }

            compareStateWithReference(2, active, new int[] {1, 2, 3});
            componentComparisons++;
            shortestPathComparisons += L2_ORDERED_PAIR_COUNT * 3;
        }

        assertEquals(16, componentComparisons);
        assertEquals(576, shortestPathComparisons);
    }

    @Test
    void sampledThreeByThreeEdgeStatesMatchIndependentReference() {
        Random stateRandom = new Random(0x5EEDL);
        int edgeCount = 12;
        int shortestPathComparisons = 0;

        for (int state = 0; state < L3_SAMPLED_STATE_COUNT; state++) {
            boolean[] active = new boolean[edgeCount];
            if (state == 0) {
                Arrays.fill(active, true);
            } else if (state > 1) {
                for (int edgeId = 0; edgeId < edgeCount; edgeId++) {
                    active[edgeId] = stateRandom.nextBoolean();
                }
            }

            compareStateWithReference(3, active, new int[] {1, 2, 4, 8});
            shortestPathComparisons += L3_ORDERED_PAIR_COUNT * 4;
        }

        assertEquals(6_912, shortestPathComparisons);
    }

    @Test
    void clusterMeasurementDoesNotInterfereWithRequestsOrFinalEdges() {
        SquareLattice measuredEveryStep = new SquareLattice(4);
        SquareLattice measuredOnlyAtEnd = new SquareLattice(4);
        SPPSimulator first = simulator(measuredEveryStep, 3, 11L, 12L);
        SPPSimulator second = simulator(measuredOnlyAtEnd, 3, 11L, 12L);
        ClusterAnalyzer analyzer = new ClusterAnalyzer();

        for (int step = 0; step < 50; step++) {
            SPPStepResult firstResult = first.step();
            analyzer.analyze(measuredEveryStep);
            SPPStepResult secondResult = second.step();
            assertEquals(firstResult, secondResult);
        }
        ClusterStats firstStats = analyzer.analyze(measuredEveryStep);
        ClusterStats secondStats = analyzer.analyze(measuredOnlyAtEnd);

        assertArrayEquals(activeState(measuredEveryStep), activeState(measuredOnlyAtEnd));
        assertArrayEquals(firstStats.componentSizes(), secondStats.componentSizes());
    }

    @Test
    void identicalExperimentConfigurationsProduceIdenticalCsv() throws IOException {
        SPPConfig first = config(1, 42L, temporaryDirectory.resolve("first"));
        SPPConfig second = config(1, 42L, temporaryDirectory.resolve("second"));

        String firstCsv = Files.readString(new SPPExperimentRunner(first).run(), StandardCharsets.UTF_8);
        String secondCsv =
                Files.readString(new SPPExperimentRunner(second).run(), StandardCharsets.UTF_8);

        assertEquals(firstCsv, secondCsv);
    }

    @Test
    void differentMeasurementIntervalsLeaveSameFinalLatticeState() {
        boolean[] measuredEveryStep = simulateWithMeasurementInterval(1);
        boolean[] measuredEverySevenSteps = simulateWithMeasurementInterval(7);

        assertArrayEquals(measuredEveryStep, measuredEverySevenSteps);
    }

    private static void compareStateWithReference(int L, boolean[] active, int[] budgets) {
        SquareLattice lattice = latticeWithState(L, active);
        ReferenceGraph reference = new ReferenceGraph(L, active);
        ClusterStats actualComponents = new ClusterAnalyzer().analyze(lattice);
        assertArrayEquals(reference.componentSizes(), actualComponents.componentSizes());

        ShortestPathFinder finder = new ShortestPathFinder(lattice);
        int vertexCount = L * L;
        for (int source = 0; source < vertexCount; source++) {
            for (int target = 0; target < vertexCount; target++) {
                if (source == target) {
                    continue;
                }
                for (int budget : budgets) {
                    int expectedDistance = reference.distance(source, target, budget);
                    Optional<ShortestPathResult> actual =
                            finder.find(source, target, budget, new Random(12345L));
                    assertEquals(
                            expectedDistance >= 0,
                            actual.isPresent(),
                            context(L, active, source, target, budget));
                    if (expectedDistance >= 0) {
                        assertEquals(
                                expectedDistance,
                                actual.orElseThrow().distance(),
                                context(L, active, source, target, budget));
                    }
                }
            }
        }
    }

    private static String context(
            int L, boolean[] active, int source, int target, int budget) {
        return "L="
                + L
                + " active="
                + Arrays.toString(active)
                + " source="
                + source
                + " target="
                + target
                + " C="
                + budget;
    }

    private static boolean[] simulateWithMeasurementInterval(long interval) {
        int L = 4;
        int C = 2;
        int maxSteps = 40;
        long runSeed = SeedUtils.runSeed(99L, 0);
        SquareLattice lattice = new SquareLattice(L);
        SPPSimulator simulator =
                simulator(
                        lattice,
                        C,
                        SeedUtils.pairSeed(runSeed),
                        SeedUtils.pathSeed(runSeed));
        ClusterAnalyzer analyzer = new ClusterAnalyzer();

        analyzer.analyze(lattice);
        while (simulator.getStep() < maxSteps && lattice.remainingEdgeCount() > 0) {
            simulator.step();
            if (simulator.getStep() % interval == 0) {
                analyzer.analyze(lattice);
            }
        }
        analyzer.analyze(lattice);
        return activeState(lattice);
    }

    private static SPPConfig config(long interval, long baseSeed, Path outputDirectory) {
        return new SPPConfig(
                4,
                2,
                2,
                30,
                interval,
                BoundaryCondition.OPEN,
                baseSeed,
                outputDirectory);
    }

    private static void assertStep(
            SPPStepResult result,
            boolean accepted,
            int pathLength,
            int removedThisStep,
            long acceptedRequests,
            long rejectedRequests) {
        assertEquals(accepted, result.accepted());
        assertEquals(pathLength, result.pathLength());
        assertEquals(removedThisStep, result.removedEdgeCount());
        assertEquals(acceptedRequests, result.acceptedRequests());
        assertEquals(rejectedRequests, result.rejectedRequests());
        assertEquals(acceptedRequests + rejectedRequests, result.step());
    }

    private static void assertState(
            SquareLattice lattice,
            ClusterAnalyzer analyzer,
            int[] expectedRemovedEdgeIds,
            int expectedRemovedCount,
            int expectedRemainingCount,
            int[] expectedComponents,
            int expectedLargest,
            int expectedSecondLargest,
            double expectedMean) {
        assertArrayEquals(expectedRemovedEdgeIds, removedEdgeIds(lattice));
        assertEquals(expectedRemovedCount, lattice.removedEdgeCount());
        assertEquals(expectedRemainingCount, lattice.remainingEdgeCount());
        ClusterStats stats = analyzer.analyze(lattice);
        assertArrayEquals(expectedComponents, stats.componentSizes());
        assertEquals(expectedLargest, stats.largestClusterSize());
        assertEquals(expectedSecondLargest, stats.secondLargestClusterSize());
        assertEquals(expectedMean, stats.meanClusterSize());
    }

    private static int[] removedEdgeIds(SquareLattice lattice) {
        int[] removed = new int[lattice.removedEdgeCount()];
        int index = 0;
        for (int edgeId = 0; edgeId < lattice.initialEdgeCount(); edgeId++) {
            if (!lattice.isEdgeActive(edgeId)) {
                removed[index++] = edgeId;
            }
        }
        return removed;
    }

    private static SquareLattice latticeWithState(int L, boolean[] active) {
        SquareLattice lattice = new SquareLattice(L);
        assertEquals(lattice.initialEdgeCount(), active.length);
        for (int edgeId = 0; edgeId < active.length; edgeId++) {
            if (!active[edgeId]) {
                lattice.removeEdge(edgeId);
            }
        }
        return lattice;
    }

    private static boolean[] activeState(SquareLattice lattice) {
        boolean[] active = new boolean[lattice.initialEdgeCount()];
        for (int edgeId = 0; edgeId < active.length; edgeId++) {
            active[edgeId] = lattice.isEdgeActive(edgeId);
        }
        return active;
    }

    private static SPPSimulator simulator(
            SquareLattice lattice, int budget, long pairSeed, long pathSeed) {
        return new SPPSimulator(
                lattice, budget, new Random(pairSeed), new Random(pathSeed));
    }

    /** Independent edge-list graph used only as the validation oracle. */
    private static final class ReferenceGraph {
        private final int vertexCount;
        private final int[] firstEndpoint;
        private final int[] secondEndpoint;
        private final boolean[] active;

        private ReferenceGraph(int L, boolean[] active) {
            this.vertexCount = L * L;
            this.firstEndpoint = new int[2 * L * (L - 1)];
            this.secondEndpoint = new int[firstEndpoint.length];
            this.active = active.clone();

            int edgeId = 0;
            for (int row = 0; row < L; row++) {
                for (int column = 0; column < L - 1; column++) {
                    firstEndpoint[edgeId] = row * L + column;
                    secondEndpoint[edgeId] = row * L + column + 1;
                    edgeId++;
                }
            }
            for (int row = 0; row < L - 1; row++) {
                for (int column = 0; column < L; column++) {
                    firstEndpoint[edgeId] = row * L + column;
                    secondEndpoint[edgeId] = (row + 1) * L + column;
                    edgeId++;
                }
            }
            if (edgeId != active.length) {
                throw new IllegalArgumentException("active edge state has the wrong length");
            }
        }

        private int distance(int source, int target, int budget) {
            int[] distance = new int[vertexCount];
            Arrays.fill(distance, -1);
            int[] queue = new int[vertexCount];
            int head = 0;
            int tail = 0;
            distance[source] = 0;
            queue[tail++] = source;

            while (head < tail) {
                int vertex = queue[head++];
                if (vertex == target) {
                    return distance[vertex];
                }
                if (distance[vertex] >= budget) {
                    continue;
                }
                for (int edgeId = 0; edgeId < active.length; edgeId++) {
                    if (!active[edgeId]) {
                        continue;
                    }
                    int neighbor = neighborAcross(edgeId, vertex);
                    if (neighbor >= 0 && distance[neighbor] < 0) {
                        distance[neighbor] = distance[vertex] + 1;
                        queue[tail++] = neighbor;
                    }
                }
            }
            return -1;
        }

        private int[] componentSizes() {
            boolean[] visited = new boolean[vertexCount];
            List<Integer> sizes = new ArrayList<>();
            int[] queue = new int[vertexCount];

            for (int start = 0; start < vertexCount; start++) {
                if (visited[start]) {
                    continue;
                }
                int head = 0;
                int tail = 0;
                visited[start] = true;
                queue[tail++] = start;
                while (head < tail) {
                    int vertex = queue[head++];
                    for (int edgeId = 0; edgeId < active.length; edgeId++) {
                        if (!active[edgeId]) {
                            continue;
                        }
                        int neighbor = neighborAcross(edgeId, vertex);
                        if (neighbor >= 0 && !visited[neighbor]) {
                            visited[neighbor] = true;
                            queue[tail++] = neighbor;
                        }
                    }
                }
                sizes.add(tail);
            }

            return sizes.stream()
                    .sorted((left, right) -> Integer.compare(right, left))
                    .mapToInt(Integer::intValue)
                    .toArray();
        }

        private int neighborAcross(int edgeId, int vertex) {
            if (firstEndpoint[edgeId] == vertex) {
                return secondEndpoint[edgeId];
            }
            if (secondEndpoint[edgeId] == vertex) {
                return firstEndpoint[edgeId];
            }
            return -1;
        }
    }
}
