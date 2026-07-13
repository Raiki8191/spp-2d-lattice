package spp;

import java.util.Arrays;
import java.util.HashSet;
import java.util.Optional;
import java.util.Random;
import java.util.Set;

import org.junit.jupiter.api.Test;

import static org.junit.jupiter.api.Assertions.assertArrayEquals;
import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.junit.jupiter.api.Assertions.assertTrue;

class ShortestPathFinderTest {
    @Test
    void findsAdjacentVerticesAtDistanceOne() {
        SquareLattice lattice = new SquareLattice(2);
        ShortestPathResult result = finder(lattice).find(0, 1, 1, new Random(1)).orElseThrow();

        assertEquals(1, result.distance());
        assertArrayEquals(new int[] {edgeIdBetween(lattice, 0, 1)}, result.edgeIds());
    }

    @Test
    void findsDiagonalVerticesAtDistanceTwo() {
        SquareLattice lattice = new SquareLattice(2);
        ShortestPathResult result = finder(lattice).find(0, 3, 2, new Random(2)).orElseThrow();

        assertEquals(2, result.distance());
        assertEquals(result.distance(), result.edgeIds().length);
    }

    @Test
    void diagonalVerticesHaveTwoSelectableShortestPaths() {
        SquareLattice lattice = new SquareLattice(2);
        ShortestPathFinder finder = finder(lattice);
        Set<String> paths = new HashSet<>();

        for (int seed = 0; seed < 100; seed++) {
            paths.add(Arrays.toString(finder.find(0, 3, 2, new Random(seed)).orElseThrow().edgeIds()));
        }

        assertEquals(2, paths.size());
    }

    @Test
    void fixedSeedReproducesSelectedPath() {
        SquareLattice lattice = new SquareLattice(3);
        ShortestPathFinder finder = finder(lattice);

        int[] first = finder.find(0, 8, 4, new Random(12345)).orElseThrow().edgeIds();
        int[] second = finder.find(0, 8, 4, new Random(12345)).orElseThrow().edgeIds();

        assertArrayEquals(first, second);
    }

    @Test
    void symmetricPathsAreNotExtremelyBiased() {
        SquareLattice lattice = new SquareLattice(2);
        ShortestPathFinder finder = finder(lattice);
        Random random = new Random(987654321);
        int horizontalFirst = edgeIdBetween(lattice, 0, 1);
        int horizontalCount = 0;
        int samples = 4_000;

        for (int i = 0; i < samples; i++) {
            int firstEdge = finder.find(0, 3, 2, random).orElseThrow().edgeIds()[0];
            if (firstEdge == horizontalFirst) {
                horizontalCount++;
            }
        }

        assertTrue(horizontalCount > samples * 0.40, "horizontalCount=" + horizontalCount);
        assertTrue(horizontalCount < samples * 0.60, "horizontalCount=" + horizontalCount);
    }

    @Test
    void returnsEmptyWhenBudgetIsBelowShortestDistance() {
        SquareLattice lattice = new SquareLattice(2);

        assertTrue(finder(lattice).find(0, 3, 1, new Random(1)).isEmpty());
    }

    @Test
    void findsPathWhenBudgetEqualsShortestDistance() {
        SquareLattice lattice = new SquareLattice(2);

        assertTrue(finder(lattice).find(0, 3, 2, new Random(1)).isPresent());
    }

    @Test
    void avoidsRemovedEdges() {
        SquareLattice lattice = new SquareLattice(2);
        int removedEdge = edgeIdBetween(lattice, 0, 1);
        lattice.removeEdge(removedEdge);

        ShortestPathResult result = finder(lattice).find(0, 3, 2, new Random(1)).orElseThrow();

        for (int edgeId : result.edgeIds()) {
            assertTrue(lattice.isEdgeActive(edgeId));
            assertFalse(edgeId == removedEdge);
        }
    }

    @Test
    void returnsEmptyAfterSourceIsDisconnected() {
        SquareLattice lattice = new SquareLattice(2);
        lattice.removeEdge(edgeIdBetween(lattice, 0, 1));
        lattice.removeEdge(edgeIdBetween(lattice, 0, 2));

        assertTrue(finder(lattice).find(0, 3, 3, new Random(1)).isEmpty());
    }

    @Test
    void returnedEdgesAreActiveAndCountMatchesDistance() {
        SquareLattice lattice = new SquareLattice(3);
        ShortestPathResult result = finder(lattice).find(0, 8, 4, new Random(9)).orElseThrow();

        assertEquals(result.distance(), result.edgeIds().length);
        for (int edgeId : result.edgeIds()) {
            assertTrue(lattice.isEdgeActive(edgeId));
        }
    }

    @Test
    void returnsEdgeIdsInSourceToTargetOrder() {
        SquareLattice lattice = new SquareLattice(3);
        int source = 0;
        int target = 8;
        ShortestPathResult result =
                finder(lattice).find(source, target, 4, new Random(17)).orElseThrow();

        int current = source;
        for (int edgeId : result.edgeIds()) {
            current = neighborAcross(lattice, current, edgeId);
        }

        assertEquals(target, current);
    }

    @Test
    void searchDoesNotChangeLatticeState() {
        SquareLattice lattice = new SquareLattice(3);
        lattice.removeEdge(0);
        boolean[] before = activeStates(lattice);
        int removedBefore = lattice.removedEdgeCount();

        Optional<ShortestPathResult> result = finder(lattice).find(0, 8, 5, new Random(4));

        assertTrue(result.isPresent());
        assertArrayEquals(before, activeStates(lattice));
        assertEquals(removedBefore, lattice.removedEdgeCount());
    }

    @Test
    void rejectsInvalidInputs() {
        SquareLattice lattice = new SquareLattice(2);
        ShortestPathFinder finder = finder(lattice);

        assertThrows(IllegalArgumentException.class, () -> new ShortestPathFinder(null));
        assertThrows(IllegalArgumentException.class, () -> finder.find(-1, 1, 1, new Random(1)));
        assertThrows(IllegalArgumentException.class,
                () -> finder.find(lattice.vertexCount(), 1, 1, new Random(1)));
        assertThrows(IllegalArgumentException.class, () -> finder.find(0, -1, 1, new Random(1)));
        assertThrows(IllegalArgumentException.class,
                () -> finder.find(0, lattice.vertexCount(), 1, new Random(1)));
        assertThrows(IllegalArgumentException.class, () -> finder.find(0, 0, 1, new Random(1)));
        assertThrows(IllegalArgumentException.class, () -> finder.find(0, 1, 0, new Random(1)));
        assertThrows(IllegalArgumentException.class, () -> finder.find(0, 1, 1, null));
    }

    private static ShortestPathFinder finder(SquareLattice lattice) {
        return new ShortestPathFinder(lattice);
    }

    private static boolean[] activeStates(SquareLattice lattice) {
        boolean[] active = new boolean[lattice.initialEdgeCount()];
        for (int edgeId = 0; edgeId < active.length; edgeId++) {
            active[edgeId] = lattice.isEdgeActive(edgeId);
        }
        return active;
    }

    private static int edgeIdBetween(SquareLattice lattice, int first, int second) {
        for (int i = 0; i < lattice.degree(first); i++) {
            if (lattice.neighbor(first, i) == second) {
                return lattice.edgeId(first, i);
            }
        }
        throw new AssertionError("vertices are not adjacent: " + first + ", " + second);
    }

    private static int neighborAcross(SquareLattice lattice, int vertexId, int edgeId) {
        for (int i = 0; i < lattice.degree(vertexId); i++) {
            if (lattice.edgeId(vertexId, i) == edgeId) {
                return lattice.neighbor(vertexId, i);
            }
        }
        throw new AssertionError("edge " + edgeId + " is not incident to vertex " + vertexId);
    }
}
