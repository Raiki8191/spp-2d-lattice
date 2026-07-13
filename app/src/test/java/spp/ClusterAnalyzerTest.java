package spp;

import static org.junit.jupiter.api.Assertions.assertArrayEquals;
import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertThrows;

import java.util.HashSet;
import java.util.Set;
import org.junit.jupiter.api.Test;

class ClusterAnalyzerTest {
    private final ClusterAnalyzer analyzer = new ClusterAnalyzer();

    @Test
    void analyzesInitialOneByOneLattice() {
        assertStats(new SquareLattice(1), new int[] {1}, 0.0);
    }

    @Test
    void analyzesInitialTwoByTwoLattice() {
        assertStats(new SquareLattice(2), new int[] {4}, 0.0);
    }

    @Test
    void analyzesInitialThreeByThreeLattice() {
        assertStats(new SquareLattice(3), new int[] {9}, 0.0);
    }

    @Test
    void detectsTwoEqualComponentsAfterDeletingCutEdges() {
        SquareLattice lattice = new SquareLattice(2);
        lattice.removeEdge(edgeIdBetween(lattice, 0, 2));
        lattice.removeEdge(edgeIdBetween(lattice, 1, 3));

        ClusterStats stats = analyzer.analyze(lattice);

        assertArrayEquals(new int[] {2, 2}, stats.componentSizes());
        assertEquals(2, stats.largestClusterSize());
        assertEquals(2, stats.secondLargestClusterSize());
        assertEquals(2.0, stats.meanClusterSize());
    }

    @Test
    void allDeletedEdgesProduceOnlyIsolatedVertices() {
        SquareLattice lattice = new SquareLattice(2);
        for (int edgeId = 0; edgeId < lattice.initialEdgeCount(); edgeId++) {
            lattice.removeEdge(edgeId);
        }

        ClusterStats stats = analyzer.analyze(lattice);

        assertArrayEquals(new int[] {1, 1, 1, 1}, stats.componentSizes());
        assertEquals(4, stats.componentCount());
        assertEquals(1, stats.largestClusterSize());
        assertEquals(1, stats.secondLargestClusterSize());
        assertEquals(1.0, stats.meanClusterSize());
    }

    @Test
    void includesIsolatedVerticesInFiniteClusterMean() {
        SquareLattice lattice = new SquareLattice(3);
        retainOnlyEdges(lattice, new int[][] {{0, 1}, {0, 3}, {1, 4}, {3, 4}, {5, 8}});

        ClusterStats stats = analyzer.analyze(lattice);

        assertArrayEquals(new int[] {4, 2, 1, 1, 1}, stats.componentSizes());
        assertEquals(7.0 / 5.0, stats.meanClusterSize());
    }

    @Test
    void excludesOnlyOneTiedLargestComponent() {
        SquareLattice lattice = new SquareLattice(3);
        retainOnlyEdges(lattice, new int[][] {{0, 1}, {1, 2}, {3, 4}, {4, 5}});

        ClusterStats stats = analyzer.analyze(lattice);

        assertArrayEquals(new int[] {3, 3, 1, 1, 1}, stats.componentSizes());
        assertEquals(3, stats.largestClusterSize());
        assertEquals(3, stats.secondLargestClusterSize());
        assertEquals(2.0, stats.meanClusterSize());
    }

    @Test
    void analysisDoesNotChangeLatticeState() {
        SquareLattice lattice = new SquareLattice(3);
        lattice.removeEdge(0);
        lattice.removeEdge(4);
        boolean[] activeBefore = activeEdges(lattice);
        int removedBefore = lattice.removedEdgeCount();
        int remainingBefore = lattice.remainingEdgeCount();

        analyzer.analyze(lattice);

        assertArrayEquals(activeBefore, activeEdges(lattice));
        assertEquals(removedBefore, lattice.removedEdgeCount());
        assertEquals(remainingBefore, lattice.remainingEdgeCount());
    }

    @Test
    void rejectsNullLattice() {
        assertThrows(IllegalArgumentException.class, () -> analyzer.analyze(null));
    }

    private void assertStats(SquareLattice lattice, int[] expectedSizes, double expectedMean) {
        ClusterStats stats = analyzer.analyze(lattice);
        assertEquals(expectedSizes.length, stats.componentCount());
        assertArrayEquals(expectedSizes, stats.componentSizes());
        assertEquals(expectedSizes[0], stats.largestClusterSize());
        assertEquals(expectedSizes.length == 1 ? 0 : expectedSizes[1], stats.secondLargestClusterSize());
        assertEquals(expectedMean, stats.meanClusterSize());
    }

    private static void retainOnlyEdges(SquareLattice lattice, int[][] keptVertexPairs) {
        Set<Integer> keptEdgeIds = new HashSet<>();
        for (int[] pair : keptVertexPairs) {
            keptEdgeIds.add(edgeIdBetween(lattice, pair[0], pair[1]));
        }
        for (int edgeId = 0; edgeId < lattice.initialEdgeCount(); edgeId++) {
            if (!keptEdgeIds.contains(edgeId)) {
                lattice.removeEdge(edgeId);
            }
        }
    }

    private static int edgeIdBetween(SquareLattice lattice, int first, int second) {
        for (int neighborIndex = 0; neighborIndex < lattice.degree(first); neighborIndex++) {
            if (lattice.neighbor(first, neighborIndex) == second) {
                return lattice.edgeId(first, neighborIndex);
            }
        }
        throw new IllegalArgumentException("vertices are not adjacent: " + first + ", " + second);
    }

    private static boolean[] activeEdges(SquareLattice lattice) {
        boolean[] active = new boolean[lattice.initialEdgeCount()];
        for (int edgeId = 0; edgeId < active.length; edgeId++) {
            active[edgeId] = lattice.isEdgeActive(edgeId);
        }
        return active;
    }
}
