package spp;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertTrue;

import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.List;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.io.TempDir;

class SPPTransitionStopTest {
    @TempDir Path temporaryDirectory;

    @Test
    void transitionStopMatchesFullRunPrefixAndWritesSummary() throws IOException {
        SPPConfig full = config(temporaryDirectory.resolve("full"), RunStopMode.MAX_STEPS_OR_ALL_EDGES, false);
        SPPConfig transition =
                config(
                        temporaryDirectory.resolve("transition"),
                        RunStopMode.TRANSITION_WINDOW_COMPLETE,
                        false);

        SPPExperimentRunner fullRunner = new SPPExperimentRunner(full);
        SPPExperimentRunner transitionRunner = new SPPExperimentRunner(transition);
        List<String> fullLines = Files.readAllLines(fullRunner.run(), StandardCharsets.UTF_8);
        List<String> transitionLines =
                Files.readAllLines(transitionRunner.run(), StandardCharsets.UTF_8);

        assertEquals(transitionLines, fullLines.subList(0, transitionLines.size()));
        String[] finalResult = transitionLines.get(transitionLines.size() - 1).split(",", -1);
        assertTrue(Double.parseDouble(finalResult[8]) <= 1.0 / transition.L());

        List<String> summary =
                Files.readAllLines(transitionRunner.runSummaryPath(), StandardCharsets.UTF_8);
        assertEquals(RunSummaryWriter.HEADER, summary.get(0));
        String[] row = summary.get(1).split(",", -1);
        assertEquals("TRANSITION_WINDOW_COMPLETE", row[6]);
        assertEquals(finalResult[3], row[2]);
        assertEquals(finalResult[4], row[3]);
        assertEquals(finalResult[6], row[4]);
        assertEquals(finalResult[8], row[5]);
    }

    @Test
    void disablingTraceDoesNotChangeResultsOrConsumeRandomness() throws IOException {
        SPPConfig traced = config(temporaryDirectory.resolve("traced"), RunStopMode.TRANSITION_WINDOW_COMPLETE, true);
        SPPConfig untraced = config(temporaryDirectory.resolve("untraced"), RunStopMode.TRANSITION_WINDOW_COMPLETE, false);
        SPPExperimentRunner tracedRunner = new SPPExperimentRunner(traced);
        SPPExperimentRunner untracedRunner = new SPPExperimentRunner(untraced);

        assertEquals(
                Files.readString(tracedRunner.run(), StandardCharsets.UTF_8),
                Files.readString(untracedRunner.run(), StandardCharsets.UTF_8));
        assertTrue(Files.isRegularFile(tracedRunner.edgeTracePath()));
        assertFalse(Files.exists(untracedRunner.edgeTracePath()));
    }

    @Test
    void halfThresholdExtendsTheSameRunWithoutChangingItsPrefix() throws IOException {
        SPPConfig original = transitionConfig(temporaryDirectory.resolve("original"), 1.0);
        SPPConfig extended = transitionConfig(temporaryDirectory.resolve("extended"), 0.5);
        SPPExperimentRunner originalRunner = new SPPExperimentRunner(original);
        SPPExperimentRunner extendedRunner = new SPPExperimentRunner(extended);

        List<String> originalLines =
                Files.readAllLines(originalRunner.run(), StandardCharsets.UTF_8);
        List<String> extendedLines =
                Files.readAllLines(extendedRunner.run(), StandardCharsets.UTF_8);

        assertEquals(originalLines, extendedLines.subList(0, originalLines.size()));
        String[] originalFinal = originalLines.get(originalLines.size() - 1).split(",", -1);
        String[] extendedFinal = extendedLines.get(extendedLines.size() - 1).split(",", -1);
        assertTrue(Double.parseDouble(originalFinal[8]) <= 1.0 / original.L());
        assertTrue(Double.parseDouble(extendedFinal[8]) <= 0.5 / extended.L());
        assertTrue(extendedLines.size() > originalLines.size());
        assertEquals(originalFinal[13], extendedFinal[13]);
        assertEquals(CsvWriter.HEADER, extendedLines.get(0));
    }

    @Test
    void maxStepsTerminationIsRecorded() throws IOException {
        SPPConfig config =
                new SPPConfig(
                        4,
                        1,
                        1,
                        1,
                        1,
                        MeasurementMode.ACCEPTED_REQUEST,
                        RunStopMode.MAX_STEPS_OR_ALL_EDGES,
                        false,
                        BoundaryCondition.OPEN,
                        42L,
                        temporaryDirectory.resolve("max"));
        SPPExperimentRunner runner = new SPPExperimentRunner(config);
        runner.run();
        String[] summary =
                Files.readAllLines(runner.runSummaryPath(), StandardCharsets.UTF_8)
                        .get(1)
                        .split(",", -1);
        assertEquals("MAX_STEPS", summary[6]);
    }

    @Test
    void allEdgesRemovedTerminationIsRecorded() throws IOException {
        SPPConfig config =
                new SPPConfig(
                        2,
                        1,
                        1,
                        10_000,
                        1,
                        MeasurementMode.ACCEPTED_REQUEST,
                        RunStopMode.MAX_STEPS_OR_ALL_EDGES,
                        false,
                        BoundaryCondition.OPEN,
                        42L,
                        temporaryDirectory.resolve("all-edges"));
        SPPExperimentRunner runner = new SPPExperimentRunner(config);
        runner.run();
        String[] summary =
                Files.readAllLines(runner.runSummaryPath(), StandardCharsets.UTF_8)
                        .get(1)
                        .split(",", -1);
        assertEquals("ALL_EDGES_REMOVED", summary[6]);
    }

    private static SPPConfig config(Path output, RunStopMode stopMode, boolean trace) {
        return new SPPConfig(
                4,
                2,
                1,
                20_000,
                1,
                MeasurementMode.ACCEPTED_REQUEST,
                stopMode,
                trace,
                BoundaryCondition.OPEN,
                42L,
                output);
    }

    private static SPPConfig transitionConfig(Path output, double multiplier) {
        return new SPPConfig(
                8,
                2,
                1,
                100_000,
                1,
                MeasurementMode.ACCEPTED_REQUEST,
                RunStopMode.TRANSITION_WINDOW_COMPLETE,
                multiplier,
                false,
                BoundaryCondition.OPEN,
                42L,
                output);
    }
}
