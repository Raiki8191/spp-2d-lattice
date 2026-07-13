package spp;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertThrows;

import java.util.Random;
import org.junit.jupiter.api.Test;

class SPPResultTest {
    private final ClusterAnalyzer analyzer = new ClusterAnalyzer();

    @Test
    void capturesInitialState() {
        SquareLattice lattice = new SquareLattice(2);
        SPPSimulator simulator = simulator(lattice, 2);

        SPPResult result = capture(3, 17L, lattice, simulator);

        assertEquals(3, result.run());
        assertEquals(2, result.L());
        assertEquals(2, result.C());
        assertEquals(0, result.step());
        assertEquals(0, result.removedEdges());
        assertEquals(4, result.remainingEdges());
        assertEquals(0.0, result.removedEdgeFraction());
        assertEquals(4, result.largestClusterSize());
        assertEquals(1.0, result.largestClusterFraction());
        assertEquals(0, result.secondLargestClusterSize());
        assertEquals(0.0, result.meanClusterSize());
        assertEquals(0, result.acceptedRequests());
        assertEquals(0, result.rejectedRequests());
        assertEquals(17L, result.seed());
    }

    @Test
    void capturesAcceptedRequestAndDerivedValues() {
        SquareLattice lattice = new SquareLattice(2);
        SPPSimulator simulator = simulator(lattice, 2);
        simulator.processRequest(0, 1);

        SPPResult result = capture(0, 29L, lattice, simulator);

        assertEquals(1, result.step());
        assertEquals(1, result.acceptedRequests());
        assertEquals(0, result.rejectedRequests());
        assertEquals(1, result.removedEdges());
        assertEquals(3, result.remainingEdges());
        assertEquals(0.25, result.removedEdgeFraction());
        assertEquals(1.0, result.largestClusterFraction());
    }

    @Test
    void capturesRejectedRequestWithoutChangingEdges() {
        SquareLattice lattice = new SquareLattice(2);
        SPPSimulator simulator = simulator(lattice, 1);
        simulator.processRequest(0, 3);

        SPPResult result = SPPResult.capture(
                0, 2, 1, 31L, lattice, simulator, analyzer.analyze(lattice));

        assertEquals(1, result.step());
        assertEquals(0, result.acceptedRequests());
        assertEquals(1, result.rejectedRequests());
        assertEquals(0, result.removedEdges());
        assertEquals(4, result.remainingEdges());
    }

    @Test
    void supportsOneByOneLatticeWithZeroInitialEdges() {
        SPPResult result =
                new SPPResult(0, 1, 1, 0, 0, 0, 0.0, 1, 1.0, 0, 0.0, 0, 0, 7);

        assertEquals(0.0, result.removedEdgeFraction());
        assertEquals(1.0, result.largestClusterFraction());
    }

    @Test
    void rejectsInvalidBasicAndCounterValues() {
        assertThrows(IllegalArgumentException.class, () -> result(-1, 2, 1, 0.0, 4, 0.0));
        assertThrows(IllegalArgumentException.class, () -> result(0, 0, 1, 0.0, 4, 0.0));
        assertThrows(IllegalArgumentException.class, () -> result(0, 2, 0, 0.0, 4, 0.0));
        assertThrows(
                IllegalArgumentException.class,
                () -> new SPPResult(0, 2, 1, 1, 0, 4, 0.0, 4, 1.0, 0, 0.0, 0, 0, 1));
    }

    @Test
    void rejectsInconsistentEdgeValuesAndFractions() {
        assertThrows(
                IllegalArgumentException.class,
                () -> new SPPResult(0, 2, 1, 0, -1, 5, -0.25, 4, 1.0, 0, 0.0, 0, 0, 1));
        assertThrows(
                IllegalArgumentException.class,
                () -> new SPPResult(0, 2, 1, 0, 5, -1, 1.25, 4, 1.0, 0, 0.0, 0, 0, 1));
        assertThrows(
                IllegalArgumentException.class,
                () -> new SPPResult(0, 2, 1, 0, 1, 4, 0.25, 4, 1.0, 0, 0.0, 0, 0, 1));
        assertThrows(IllegalArgumentException.class, () -> result(0, 2, 1, 0.5, 4, 0.0));
    }

    @Test
    void rejectsInvalidClusterValues() {
        assertThrows(IllegalArgumentException.class, () -> result(0, 2, 1, 0.0, 0, 0.0));
        assertThrows(IllegalArgumentException.class, () -> result(0, 2, 1, 0.0, 5, 0.0));
        assertThrows(
                IllegalArgumentException.class,
                () -> new SPPResult(0, 2, 1, 0, 0, 4, 0.0, 3, 0.75, 4, 1.0, 0, 0, 1));
        assertThrows(IllegalArgumentException.class, () -> result(0, 2, 1, 0.0, 4, -1.0));
    }

    @Test
    void rejectsNonFiniteMeansAndFractions() {
        assertThrows(IllegalArgumentException.class, () -> result(0, 2, 1, 0.0, 4, Double.NaN));
        assertThrows(
                IllegalArgumentException.class,
                () -> result(0, 2, 1, 0.0, 4, Double.POSITIVE_INFINITY));
        assertThrows(
                IllegalArgumentException.class,
                () -> result(0, 2, 1, Double.NaN, 4, 0.0));
        assertThrows(
                IllegalArgumentException.class,
                () -> result(0, 2, 1, Double.NEGATIVE_INFINITY, 4, 0.0));
    }

    @Test
    void captureRejectsNullAndMismatchedInputs() {
        SquareLattice lattice = new SquareLattice(2);
        SPPSimulator simulator = simulator(lattice, 2);
        ClusterStats stats = analyzer.analyze(lattice);

        assertThrows(
                IllegalArgumentException.class,
                () -> SPPResult.capture(0, 2, 2, 1, null, simulator, stats));
        assertThrows(
                IllegalArgumentException.class,
                () -> SPPResult.capture(0, 2, 2, 1, lattice, null, stats));
        assertThrows(
                IllegalArgumentException.class,
                () -> SPPResult.capture(0, 2, 2, 1, lattice, simulator, null));
        assertThrows(
                IllegalArgumentException.class,
                () -> SPPResult.capture(0, 3, 2, 1, lattice, simulator, stats));
        assertThrows(
                IllegalArgumentException.class,
                () -> SPPResult.capture(
                        0,
                        2,
                        2,
                        1,
                        lattice,
                        simulator,
                        new ClusterStats(1, 3, 0, 0.0, new int[] {3})));
    }

    private SPPResult capture(
            int run, long seed, SquareLattice lattice, SPPSimulator simulator) {
        return SPPResult.capture(
                run, 2, 2, seed, lattice, simulator, analyzer.analyze(lattice));
    }

    private static SPPSimulator simulator(SquareLattice lattice, int budget) {
        return new SPPSimulator(lattice, budget, new Random(1), new Random(2));
    }

    private static SPPResult result(
            int run, int L, int C, double removedFraction, int largest, double mean) {
        return new SPPResult(
                run,
                L,
                C,
                0,
                0,
                2L * L * (L - 1L),
                removedFraction,
                largest,
                (double) largest / ((long) L * L),
                0,
                mean,
                0,
                0,
                1);
    }
}
