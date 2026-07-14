package spp;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertArrayEquals;
import static org.junit.jupiter.api.Assertions.assertTrue;

import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.Random;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.io.TempDir;

class AcceptedRequestMeasurementTest {
    @TempDir Path temporaryDirectory;

    @Test
    void writesInitialAcceptedAndUnmeasuredFinalStatesOnly() throws IOException {
        SPPConfig config = acceptedConfig(3, 1, 1, 12, 999, 42L, temporaryDirectory);
        Replay replay = replay(config);
        List<String[]> rows = rows(new SPPExperimentRunner(config).run());

        assertEquals(expectedMeasurementSteps(replay), steps(rows));
        assertEquals(0L, Long.parseLong(rows.get(0)[3]));

        Map<Long, SPPStepResult> resultByStep = new HashMap<>();
        for (SPPStepResult result : replay.results()) {
            resultByStep.put(result.step(), result);
        }
        for (int index = 1; index < rows.size(); index++) {
            String[] previous = rows.get(index - 1);
            String[] current = rows.get(index);
            long step = Long.parseLong(current[3]);
            SPPStepResult result = resultByStep.get(step);
            long removedIncrease = Long.parseLong(current[4]) - Long.parseLong(previous[4]);

            if (result.accepted()) {
                assertEquals(result.pathLength(), removedIncrease);
                assertEquals(result.removedEdgeCount(), removedIncrease);
            } else {
                assertEquals(rows.size() - 1, index);
                assertEquals(0L, removedIncrease);
            }
        }

        for (int index = 1; index < rows.size() - 1; index++) {
            assertTrue(Long.parseLong(rows.get(index)[4]) > Long.parseLong(rows.get(index - 1)[4]));
        }
        assertCsvInvariants(rows, config.L());
    }

    @Test
    void rejectedRequestsDoNotCreateIntermediateRowsAndStepsMayJump() throws IOException {
        SPPConfig config = acceptedConfig(3, 1, 1, 30, 1, 42L, temporaryDirectory);
        Replay replay = replay(config);
        List<String[]> rows = rows(new SPPExperimentRunner(config).run());
        List<Long> measuredSteps = steps(rows);

        assertEquals(expectedMeasurementSteps(replay), measuredSteps);
        assertTrue(
                replay.results().stream().anyMatch(result -> !result.accepted()),
                "validation seed must contain rejected requests");
        boolean hasStepGap = false;
        for (int index = 1; index < measuredSteps.size(); index++) {
            if (measuredSteps.get(index) - measuredSteps.get(index - 1) > 1) {
                hasStepGap = true;
                break;
            }
        }
        assertTrue(
                hasStepGap,
                "accepted-request measurements should allow skipped rejected requests");
    }

    @Test
    void maxStepsZeroWritesOnlyInitialRow() throws IOException {
        SPPConfig config = acceptedConfig(3, 1, 1, 0, 1, 42L, temporaryDirectory);

        List<String[]> rows = rows(new SPPExperimentRunner(config).run());

        assertEquals(1, rows.size());
        assertEquals("0", rows.get(0)[3]);
    }

    @Test
    void rejectedFinalRequestIsWrittenAsFinalState() throws IOException {
        SPPConfig config = findConfigurationEndingInRejection();
        Replay replay = replay(config);
        List<String[]> rows = rows(new SPPExperimentRunner(config).run());
        SPPStepResult finalResult = replay.results().get(replay.results().size() - 1);

        assertTrue(!finalResult.accepted());
        assertEquals(finalResult.step(), Long.parseLong(rows.get(rows.size() - 1)[3]));
        assertEquals(
                rows.get(rows.size() - 2)[4],
                rows.get(rows.size() - 1)[4],
                "a rejected final request must preserve removed_edges");
    }

    @Test
    void allEdgesRemovedFinalStepIsNotDuplicated() throws IOException {
        SPPConfig config = acceptedConfig(2, 1, 1, 10_000, 7, 42L, temporaryDirectory);
        List<String[]> rows = rows(new SPPExperimentRunner(config).run());
        String[] last = rows.get(rows.size() - 1);
        long finalStep = Long.parseLong(last[3]);

        assertEquals("0", last[5]);
        assertEquals(1, rows.stream().filter(row -> Long.parseLong(row[3]) == finalStep).count());
    }

    @Test
    void sameConfigurationAndSeedProduceIdenticalCsv() throws IOException {
        SPPConfig first =
                acceptedConfig(4, 2, 2, 30, 5, 77L, temporaryDirectory.resolve("first"));
        SPPConfig second =
                acceptedConfig(4, 2, 2, 30, 99, 77L, temporaryDirectory.resolve("second"));

        String firstCsv = Files.readString(new SPPExperimentRunner(first).run(), StandardCharsets.UTF_8);
        String secondCsv =
                Files.readString(new SPPExperimentRunner(second).run(), StandardCharsets.UTF_8);

        assertEquals(
                firstCsv,
                secondCsv,
                "measurementInterval is ignored in ACCEPTED_REQUEST mode");
    }

    @Test
    void measurementModeDoesNotChangeFinalSimulationState() throws IOException {
        SPPConfig stepInterval =
                config(
                        4,
                        2,
                        1,
                        40,
                        7,
                        MeasurementMode.STEP_INTERVAL,
                        91L,
                        temporaryDirectory.resolve("step"));
        SPPConfig acceptedEvent =
                config(
                        4,
                        2,
                        1,
                        40,
                        7,
                        MeasurementMode.ACCEPTED_REQUEST,
                        91L,
                        temporaryDirectory.resolve("accepted"));

        List<String[]> stepRows = rows(new SPPExperimentRunner(stepInterval).run());
        List<String[]> acceptedRows = rows(new SPPExperimentRunner(acceptedEvent).run());

        assertArrayEquals(
                stepRows.get(stepRows.size() - 1),
                acceptedRows.get(acceptedRows.size() - 1),
                "final 14-column state must be identical");
    }

    private SPPConfig findConfigurationEndingInRejection() {
        for (long baseSeed = 0; baseSeed < 1_000; baseSeed++) {
            SPPConfig candidate =
                    acceptedConfig(
                            3,
                            1,
                            1,
                            10,
                            5,
                            baseSeed,
                            temporaryDirectory.resolve("final-rejected-" + baseSeed));
            Replay replay = replay(candidate);
            if (!replay.results().isEmpty()
                    && !replay.results().get(replay.results().size() - 1).accepted()
                    && replay.results().stream().anyMatch(SPPStepResult::accepted)) {
                return candidate;
            }
        }
        throw new AssertionError("could not find deterministic final-rejection validation seed");
    }

    private static Replay replay(SPPConfig config) {
        SquareLattice lattice = new SquareLattice(config.L());
        long runSeed = SeedUtils.runSeed(config.baseSeed(), 0);
        SPPSimulator simulator =
                new SPPSimulator(
                        lattice,
                        config.C(),
                        new Random(SeedUtils.pairSeed(runSeed)),
                        new Random(SeedUtils.pathSeed(runSeed)));
        List<SPPStepResult> results = new ArrayList<>();
        while (simulator.getStep() < config.maxSteps() && lattice.remainingEdgeCount() > 0) {
            results.add(simulator.step());
        }
        return new Replay(results);
    }

    private static List<Long> expectedMeasurementSteps(Replay replay) {
        List<Long> expected = new ArrayList<>();
        expected.add(0L);
        for (SPPStepResult result : replay.results()) {
            if (result.accepted()) {
                expected.add(result.step());
            }
        }
        if (!replay.results().isEmpty()) {
            long finalStep = replay.results().get(replay.results().size() - 1).step();
            if (expected.get(expected.size() - 1) != finalStep) {
                expected.add(finalStep);
            }
        }
        return expected;
    }

    private static void assertCsvInvariants(List<String[]> rows, int L) {
        long initialEdges = 2L * L * (L - 1L);
        for (String[] row : rows) {
            assertEquals(14, row.length);
            assertEquals(
                    Long.parseLong(row[3]),
                    Long.parseLong(row[11]) + Long.parseLong(row[12]));
            assertEquals(
                    initialEdges,
                    Long.parseLong(row[4]) + Long.parseLong(row[5]));
        }
    }

    private static List<String[]> rows(Path path) throws IOException {
        List<String> lines = Files.readAllLines(path, StandardCharsets.UTF_8);
        List<String[]> rows = new ArrayList<>();
        for (int index = 1; index < lines.size(); index++) {
            rows.add(lines.get(index).split(",", -1));
        }
        return rows;
    }

    private static List<Long> steps(List<String[]> rows) {
        return rows.stream().map(row -> Long.parseLong(row[3])).toList();
    }

    private static SPPConfig acceptedConfig(
            int L,
            int C,
            int runs,
            long maxSteps,
            long interval,
            long baseSeed,
            Path outputDirectory) {
        return config(
                L,
                C,
                runs,
                maxSteps,
                interval,
                MeasurementMode.ACCEPTED_REQUEST,
                baseSeed,
                outputDirectory);
    }

    private static SPPConfig config(
            int L,
            int C,
            int runs,
            long maxSteps,
            long interval,
            MeasurementMode mode,
            long baseSeed,
            Path outputDirectory) {
        return new SPPConfig(
                L,
                C,
                runs,
                maxSteps,
                interval,
                mode,
                BoundaryCondition.OPEN,
                baseSeed,
                outputDirectory);
    }

    private record Replay(List<SPPStepResult> results) {}
}
