package spp;

import java.util.Random;

import org.junit.jupiter.api.Test;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.junit.jupiter.api.Assertions.assertTrue;

class SPPSimulatorTest {
    @Test
    void acceptsAdjacentRequestAndRemovesOneEdge() {
        SquareLattice lattice = new SquareLattice(2);
        SPPStepResult result = simulator(lattice, 2).processRequest(0, 1);

        assertTrue(result.accepted());
        assertEquals(1, result.pathLength());
        assertEquals(1, result.removedEdgeCount());
        assertEquals(1, lattice.removedEdgeCount());
    }

    @Test
    void acceptsDiagonalRequestAndRemovesTwoEdges() {
        SquareLattice lattice = new SquareLattice(2);
        SPPStepResult result = simulator(lattice, 2).processRequest(0, 3);

        assertTrue(result.accepted());
        assertEquals(2, result.pathLength());
        assertEquals(2, result.removedEdgeCount());
        assertEquals(2, lattice.removedEdgeCount());
    }

    @Test
    void nextRequestUsesUpdatedLattice() {
        SquareLattice lattice = new SquareLattice(2);
        SPPSimulator simulator = simulator(lattice, 1);

        assertTrue(simulator.processRequest(0, 1).accepted());
        SPPStepResult second = simulator.processRequest(0, 1);

        assertFalse(second.accepted());
        assertEquals(1, lattice.removedEdgeCount());
    }

    @Test
    void rejectsUnreachableRequest() {
        SquareLattice lattice = new SquareLattice(2);
        lattice.removeEdge(edgeIdBetween(lattice, 0, 1));
        lattice.removeEdge(edgeIdBetween(lattice, 0, 2));

        SPPStepResult result = simulator(lattice, 3).processRequest(0, 3);

        assertFalse(result.accepted());
        assertEquals(-1, result.pathLength());
        assertEquals(0, result.removedEdgeCount());
    }

    @Test
    void rejectsWhenBudgetIsInsufficientWithoutChangingEdges() {
        SquareLattice lattice = new SquareLattice(2);
        int removedBefore = lattice.removedEdgeCount();
        int remainingBefore = lattice.remainingEdgeCount();

        SPPStepResult result = simulator(lattice, 1).processRequest(0, 3);

        assertFalse(result.accepted());
        assertEquals(removedBefore, lattice.removedEdgeCount());
        assertEquals(remainingBefore, lattice.remainingEdgeCount());
    }

    @Test
    void countersAlwaysSumToStep() {
        SquareLattice lattice = new SquareLattice(2);
        SPPSimulator simulator = simulator(lattice, 1);

        SPPStepResult first = simulator.processRequest(0, 1);
        SPPStepResult second = simulator.processRequest(0, 3);

        assertEquals(first.step(), first.acceptedRequests() + first.rejectedRequests());
        assertEquals(second.step(), second.acceptedRequests() + second.rejectedRequests());
        assertEquals(simulator.getStep(), simulator.getAcceptedRequests() + simulator.getRejectedRequests());
    }

    @Test
    void processRequestPreservesSpecifiedEndpoints() {
        SPPStepResult result = simulator(new SquareLattice(2), 2).processRequest(2, 1);

        assertEquals(2, result.source());
        assertEquals(1, result.target());
    }

    @Test
    void randomStepAlwaysSelectsDistinctVertices() {
        SPPSimulator simulator = new SPPSimulator(
                new SquareLattice(3), 4, new Random(111), new Random(222));

        for (int i = 0; i < 1_000; i++) {
            SPPStepResult result = simulator.step();
            assertTrue(result.source() >= 0 && result.source() < 9);
            assertTrue(result.target() >= 0 && result.target() < 9);
            assertFalse(result.source() == result.target());
        }
    }

    @Test
    void fixedSeedsReproduceRequestsAndResults() {
        SPPSimulator first = new SPPSimulator(
                new SquareLattice(3), 4, new Random(123), new Random(456));
        SPPSimulator second = new SPPSimulator(
                new SquareLattice(3), 4, new Random(123), new Random(456));

        for (int i = 0; i < 50; i++) {
            assertEquals(first.step(), second.step());
        }
    }

    @Test
    void pathRandomConsumptionDoesNotChangePairSequence() {
        Random firstPathRandom = new Random(456);
        Random secondPathRandom = new Random(456);
        for (int i = 0; i < 100; i++) {
            secondPathRandom.nextLong();
        }
        SPPSimulator first = new SPPSimulator(
                new SquareLattice(3), 4, new Random(123), firstPathRandom);
        SPPSimulator second = new SPPSimulator(
                new SquareLattice(3), 4, new Random(123), secondPathRandom);

        for (int i = 0; i < 100; i++) {
            SPPStepResult firstResult = first.step();
            SPPStepResult secondResult = second.step();
            assertEquals(firstResult.source(), secondResult.source());
            assertEquals(firstResult.target(), secondResult.target());
        }
    }

    @Test
    void acceptedAndRejectedResultsHaveConsistentPayloads() {
        SPPSimulator acceptedSimulator = simulator(new SquareLattice(2), 2);
        SPPStepResult accepted = acceptedSimulator.processRequest(0, 3);

        SPPSimulator rejectedSimulator = simulator(new SquareLattice(2), 1);
        SPPStepResult rejected = rejectedSimulator.processRequest(0, 3);

        assertEquals(accepted.pathLength(), accepted.removedEdgeCount());
        assertEquals(-1, rejected.pathLength());
        assertEquals(0, rejected.removedEdgeCount());
    }

    @Test
    void rejectsInvalidRequestEndpointsWithoutAdvancingState() {
        SPPSimulator simulator = simulator(new SquareLattice(2), 2);

        assertThrows(IllegalArgumentException.class, () -> simulator.processRequest(-1, 1));
        assertThrows(IllegalArgumentException.class, () -> simulator.processRequest(0, -1));
        assertThrows(IllegalArgumentException.class, () -> simulator.processRequest(4, 1));
        assertThrows(IllegalArgumentException.class, () -> simulator.processRequest(0, 4));
        assertThrows(IllegalArgumentException.class, () -> simulator.processRequest(1, 1));
        assertEquals(0, simulator.getStep());
    }

    @Test
    void rejectsInvalidConstructorArguments() {
        SquareLattice lattice = new SquareLattice(2);
        Random random = new Random(1);

        assertThrows(IllegalArgumentException.class,
                () -> new SPPSimulator(null, 1, random, random));
        assertThrows(IllegalArgumentException.class,
                () -> new SPPSimulator(lattice, 0, random, random));
        assertThrows(IllegalArgumentException.class,
                () -> new SPPSimulator(lattice, 1, null, random));
        assertThrows(IllegalArgumentException.class,
                () -> new SPPSimulator(lattice, 1, random, null));
        assertThrows(IllegalArgumentException.class,
                () -> new SPPSimulator(new SquareLattice(1), 1, random, random));
    }

    private static SPPSimulator simulator(SquareLattice lattice, int budget) {
        return new SPPSimulator(lattice, budget, new Random(123), new Random(456));
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
