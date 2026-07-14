package spp;

import static org.junit.jupiter.api.Assertions.assertArrayEquals;
import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.junit.jupiter.api.Assertions.assertTrue;

import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.HashSet;
import java.util.List;
import java.util.Map;
import java.util.Random;
import java.util.Set;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.io.TempDir;

class EdgeRemovalTraceTest {
    @TempDir Path temporaryDirectory;

    @Test
    void fixedL2RequestsProduceExpectedContiguousTrace() throws IOException {
        Path trace = temporaryDirectory.resolve("edge_removals.csv");
        SquareLattice lattice = new SquareLattice(2);
        try (EdgeRemovalTraceWriter writer = EdgeRemovalTraceWriter.create(trace)) {
            SPPSimulator simulator =
                    new SPPSimulator(
                            lattice,
                            1,
                            new Random(1),
                            new Random(2),
                            writer.observerForRun(0, 99L));
            simulator.processRequest(0, 1);
            simulator.processRequest(1, 3);
            simulator.processRequest(3, 2);
            simulator.processRequest(2, 0);
        }

        List<String[]> rows = rows(trace);
        assertEquals(4, rows.size());
        assertArrayEquals(new int[] {0, 3, 1, 2}, column(rows, 5));
        assertArrayEquals(new int[] {0, 1, 2, 3}, column(rows, 1));
        assertArrayEquals(new int[] {1, 2, 3, 4}, column(rows, 2));
        assertArrayEquals(new int[] {0, 1, 3, 2}, column(rows, 6));
        assertArrayEquals(new int[] {1, 3, 2, 0}, column(rows, 7));
        assertTrue(rows.stream().allMatch(row -> row[3].equals("0")));
        assertTrue(rows.stream().allMatch(row -> row[4].equals("1")));
        assertTrue(rows.stream().allMatch(row -> row[8].equals("99")));
    }

    @Test
    void pathRowsFollowSourceToTargetAndRejectedRequestProducesNoRows() throws IOException {
        Path trace = temporaryDirectory.resolve("path-order.csv");
        SquareLattice lattice = new SquareLattice(2);
        List<int[]> selectedPaths = new ArrayList<>();
        try (EdgeRemovalTraceWriter writer = EdgeRemovalTraceWriter.create(trace)) {
            EdgeRemovalObserver traceObserver = writer.observerForRun(4, 1234L);
            SPPSimulator simulator =
                    new SPPSimulator(
                            lattice,
                            3,
                            new Random(1),
                            new Random(456),
                            (step, source, target, path) -> {
                                selectedPaths.add(path.edgeIds());
                                traceObserver.edgesRemoved(step, source, target, path);
                            });
            assertTrue(simulator.processRequest(0, 3).accepted());
            int[] removedEndpoints = endpoints(2, selectedPaths.get(0)[0]);
            assertFalse(
                    simulator.processRequest(removedEndpoints[0], removedEndpoints[1]).accepted());
        }

        List<String[]> rows = rows(trace);
        assertEquals(2, rows.size());
        assertArrayEquals(new int[] {0, 1}, column(rows, 3));
        assertTrue(rows.stream().allMatch(row -> row[2].equals("1")));
        assertTrue(rows.stream().allMatch(row -> row[4].equals("2")));
        assertPathConnects(2, 0, 3, column(rows, 5));
    }

    @Test
    void experimentTraceMatchesFinalRemovedEdgesAndKeepsResultsSchema() throws IOException {
        SPPConfig config = config(temporaryDirectory.resolve("experiment"), 2, 25, 7L);
        SPPExperimentRunner runner = new SPPExperimentRunner(config);
        Path result = runner.run();

        List<String> resultLines = Files.readAllLines(result, StandardCharsets.UTF_8);
        assertEquals(14, resultLines.get(0).split(",", -1).length);
        Map<Integer, Integer> finalRemoved = new HashMap<>();
        for (String line : resultLines.subList(1, resultLines.size())) {
            String[] fields = line.split(",", -1);
            finalRemoved.put(Integer.parseInt(fields[0]), Integer.parseInt(fields[4]));
        }

        Map<Integer, List<String[]>> traceByRun = new HashMap<>();
        for (String[] row : rows(runner.edgeTracePath())) {
            traceByRun.computeIfAbsent(Integer.parseInt(row[0]), ignored -> new ArrayList<>())
                    .add(row);
        }
        for (int run = 0; run < config.runs(); run++) {
            List<String[]> runRows = traceByRun.getOrDefault(run, List.of());
            assertEquals(finalRemoved.get(run).intValue(), runRows.size());
            Set<Integer> edgeIds = new HashSet<>();
            for (int index = 0; index < runRows.size(); index++) {
                assertEquals(index, Integer.parseInt(runRows.get(index)[1]));
                assertTrue(edgeIds.add(Integer.parseInt(runRows.get(index)[5])));
                assertEquals(
                        SeedUtils.runSeed(config.baseSeed(), run),
                        Long.parseLong(runRows.get(index)[8]));
            }
        }
    }

    @Test
    void tracingDoesNotChangeSimulationAndIsReproducible() throws IOException {
        SPPConfig first = config(temporaryDirectory.resolve("first"), 2, 30, 42L);
        SPPConfig second = config(temporaryDirectory.resolve("second"), 2, 30, 42L);
        SPPExperimentRunner firstRunner = new SPPExperimentRunner(first);
        SPPExperimentRunner secondRunner = new SPPExperimentRunner(second);

        Path firstResult = firstRunner.run();
        Path secondResult = secondRunner.run();
        assertEquals(Files.readString(firstResult), Files.readString(secondResult));
        assertEquals(
                Files.readString(firstRunner.edgeTracePath()),
                Files.readString(secondRunner.edgeTracePath()));

        SquareLattice untracedLattice = new SquareLattice(3);
        SquareLattice tracedLattice = new SquareLattice(3);
        List<int[]> observed = new ArrayList<>();
        SPPSimulator untraced =
                new SPPSimulator(untracedLattice, 2, new Random(5), new Random(6));
        SPPSimulator traced =
                new SPPSimulator(
                        tracedLattice,
                        2,
                        new Random(5),
                        new Random(6),
                        (step, source, target, path) -> observed.add(path.edgeIds()));
        for (int step = 0; step < 20; step++) {
            assertEquals(untraced.step(), traced.step());
        }
        for (int edgeId = 0; edgeId < untracedLattice.initialEdgeCount(); edgeId++) {
            assertEquals(
                    untracedLattice.isEdgeActive(edgeId), tracedLattice.isEdgeActive(edgeId));
        }
        assertFalse(observed.isEmpty());
    }

    @Test
    void rejectsNullObserver() {
        assertThrows(
                IllegalArgumentException.class,
                () ->
                        new SPPSimulator(
                                new SquareLattice(2),
                                1,
                                new Random(1),
                                new Random(2),
                                null));
    }

    private static SPPConfig config(Path root, int budget, long maxSteps, long seed) {
        return new SPPConfig(
                3,
                budget,
                2,
                maxSteps,
                4,
                MeasurementMode.ACCEPTED_REQUEST,
                BoundaryCondition.OPEN,
                seed,
                root);
    }

    private static List<String[]> rows(Path path) throws IOException {
        return Files.readAllLines(path, StandardCharsets.UTF_8).stream()
                .skip(1)
                .map(line -> line.split(",", -1))
                .toList();
    }

    private static int[] column(List<String[]> rows, int index) {
        return rows.stream().mapToInt(row -> Integer.parseInt(row[index])).toArray();
    }

    private static void assertPathConnects(int L, int source, int target, int[] edgeIds) {
        int current = source;
        for (int edgeId : edgeIds) {
            int[] endpoints = endpoints(L, edgeId);
            if (endpoints[0] == current) {
                current = endpoints[1];
            } else {
                assertEquals(endpoints[1], current);
                current = endpoints[0];
            }
        }
        assertEquals(target, current);
    }

    private static int[] endpoints(int L, int edgeId) {
        int horizontalCount = L * (L - 1);
        if (edgeId < horizontalCount) {
            int row = edgeId / (L - 1);
            int column = edgeId % (L - 1);
            int left = row * L + column;
            return new int[] {left, left + 1};
        }
        int verticalIndex = edgeId - horizontalCount;
        int row = verticalIndex / L;
        int column = verticalIndex % L;
        int top = row * L + column;
        return new int[] {top, top + L};
    }
}
