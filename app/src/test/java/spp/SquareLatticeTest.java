package spp;

import org.junit.jupiter.api.Test;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.junit.jupiter.api.Assertions.assertTrue;

class SquareLatticeTest {
    @Test
    void computesVertexAndEdgeCountsForSmallLattices() {
        assertCounts(new SquareLattice(1), 1, 0);
        assertCounts(new SquareLattice(2), 4, 4);
        assertCounts(new SquareLattice(3), 9, 12);
    }

    @Test
    void singleVertexHasDegreeZero() {
        assertEquals(0, new SquareLattice(1).degree(0));
    }

    @Test
    void everyVertexInTwoByTwoLatticeHasDegreeTwo() {
        SquareLattice lattice = new SquareLattice(2);

        for (int vertexId = 0; vertexId < lattice.vertexCount(); vertexId++) {
            assertEquals(2, lattice.degree(vertexId));
        }
    }

    @Test
    void threeByThreeLatticeHasExpectedDegrees() {
        SquareLattice lattice = new SquareLattice(3);
        int[] expected = {
            2, 3, 2,
            3, 4, 3,
            2, 3, 2
        };

        for (int vertexId = 0; vertexId < expected.length; vertexId++) {
            assertEquals(expected[vertexId], lattice.degree(vertexId));
        }
    }

    @Test
    void convertsBetweenCoordinatesAndVertexIds() {
        SquareLattice lattice = new SquareLattice(3);

        for (int row = 0; row < lattice.sideLength(); row++) {
            for (int column = 0; column < lattice.sideLength(); column++) {
                int vertexId = lattice.vertexId(row, column);
                assertEquals(row * lattice.sideLength() + column, vertexId);
                assertEquals(row, lattice.rowOf(vertexId));
                assertEquals(column, lattice.columnOf(vertexId));
            }
        }
    }

    @Test
    void edgeIdsAreContiguousAndEachAppearsExactlyTwice() {
        SquareLattice lattice = new SquareLattice(3);
        int[] occurrences = new int[lattice.initialEdgeCount()];

        for (int vertexId = 0; vertexId < lattice.vertexCount(); vertexId++) {
            for (int neighborIndex = 0; neighborIndex < lattice.degree(vertexId); neighborIndex++) {
                occurrences[lattice.edgeId(vertexId, neighborIndex)]++;
            }
        }

        for (int edgeId = 0; edgeId < occurrences.length; edgeId++) {
            assertEquals(2, occurrences[edgeId], "edgeId=" + edgeId);
        }
    }

    @Test
    void bothEndpointsReferToTheSameEdgeId() {
        SquareLattice lattice = new SquareLattice(3);

        for (int vertexId = 0; vertexId < lattice.vertexCount(); vertexId++) {
            for (int neighborIndex = 0; neighborIndex < lattice.degree(vertexId); neighborIndex++) {
                int neighbor = lattice.neighbor(vertexId, neighborIndex);
                int edgeId = lattice.edgeId(vertexId, neighborIndex);
                assertTrue(hasAdjacency(neighbor, vertexId, edgeId, lattice));
            }
        }
    }

    @Test
    void assignsHorizontalThenVerticalEdgeIdsInRowMajorOrder() {
        SquareLattice lattice = new SquareLattice(3);

        assertEquals(0, edgeIdBetween(lattice, lattice.vertexId(0, 0), lattice.vertexId(0, 1)));
        assertEquals(5, edgeIdBetween(lattice, lattice.vertexId(2, 1), lattice.vertexId(2, 2)));
        assertEquals(6, edgeIdBetween(lattice, lattice.vertexId(0, 0), lattice.vertexId(1, 0)));
        assertEquals(11, edgeIdBetween(lattice, lattice.vertexId(1, 2), lattice.vertexId(2, 2)));
    }

    @Test
    void removesEdgeAndUpdatesCounts() {
        SquareLattice lattice = new SquareLattice(2);

        assertTrue(lattice.removeEdge(0));
        assertFalse(lattice.isEdgeActive(0));
        assertEquals(1, lattice.removedEdgeCount());
        assertEquals(3, lattice.remainingEdgeCount());
    }

    @Test
    void removingSameEdgeTwiceDoesNotDoubleCount() {
        SquareLattice lattice = new SquareLattice(2);

        assertTrue(lattice.removeEdge(0));
        assertFalse(lattice.removeEdge(0));
        assertEquals(1, lattice.removedEdgeCount());
        assertEquals(3, lattice.remainingEdgeCount());
    }

    @Test
    void resetReactivatesEveryEdge() {
        SquareLattice lattice = new SquareLattice(3);
        lattice.removeEdge(0);
        lattice.removeEdge(lattice.initialEdgeCount() - 1);

        lattice.resetEdges();

        assertEquals(0, lattice.removedEdgeCount());
        assertEquals(lattice.initialEdgeCount(), lattice.remainingEdgeCount());
        for (int edgeId = 0; edgeId < lattice.initialEdgeCount(); edgeId++) {
            assertTrue(lattice.isEdgeActive(edgeId));
        }
    }

    @Test
    void rejectsInvalidSideLength() {
        assertThrows(IllegalArgumentException.class, () -> new SquareLattice(0));
        assertThrows(IllegalArgumentException.class, () -> new SquareLattice(24_000));
        assertThrows(IllegalArgumentException.class, () -> new SquareLattice(40_000));
        assertThrows(IllegalArgumentException.class, () -> new SquareLattice(50_000));
    }

    @Test
    void rejectsInvalidCoordinates() {
        SquareLattice lattice = new SquareLattice(2);

        assertThrows(IllegalArgumentException.class, () -> lattice.vertexId(-1, 0));
        assertThrows(IllegalArgumentException.class, () -> lattice.vertexId(0, -1));
        assertThrows(IllegalArgumentException.class, () -> lattice.vertexId(2, 0));
        assertThrows(IllegalArgumentException.class, () -> lattice.vertexId(0, 2));
    }

    @Test
    void rejectsInvalidVertexIdsAndNeighborIndices() {
        SquareLattice lattice = new SquareLattice(2);

        assertThrows(IllegalArgumentException.class, () -> lattice.degree(-1));
        assertThrows(IllegalArgumentException.class, () -> lattice.rowOf(lattice.vertexCount()));
        assertThrows(IllegalArgumentException.class, () -> lattice.columnOf(lattice.vertexCount()));
        assertThrows(IllegalArgumentException.class, () -> lattice.neighbor(0, -1));
        assertThrows(IllegalArgumentException.class, () -> lattice.edgeId(0, lattice.degree(0)));
    }

    @Test
    void rejectsInvalidEdgeIds() {
        SquareLattice lattice = new SquareLattice(2);

        assertThrows(IllegalArgumentException.class, () -> lattice.isEdgeActive(-1));
        assertThrows(IllegalArgumentException.class,
                () -> lattice.removeEdge(lattice.initialEdgeCount()));
    }

    private static void assertCounts(SquareLattice lattice, int vertices, int edges) {
        assertEquals(vertices, lattice.vertexCount());
        assertEquals(edges, lattice.initialEdgeCount());
        assertEquals(edges, lattice.remainingEdgeCount());
        assertEquals(0, lattice.removedEdgeCount());
    }

    private static boolean hasAdjacency(
            int vertexId, int expectedNeighbor, int expectedEdgeId, SquareLattice lattice) {
        for (int i = 0; i < lattice.degree(vertexId); i++) {
            if (lattice.neighbor(vertexId, i) == expectedNeighbor
                    && lattice.edgeId(vertexId, i) == expectedEdgeId) {
                return true;
            }
        }
        return false;
    }

    private static int edgeIdBetween(SquareLattice lattice, int first, int second) {
        for (int i = 0; i < lattice.degree(first); i++) {
            if (lattice.neighbor(first, i) == second) {
                return lattice.edgeId(first, i);
            }
        }
        throw new AssertionError("vertices are not adjacent: " + first + ", " + second);
    }
}
