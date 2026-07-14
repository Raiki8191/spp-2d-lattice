package spp;

import static org.junit.jupiter.api.Assertions.assertArrayEquals;
import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertNotEquals;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.junit.jupiter.api.Assertions.assertTrue;

import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.List;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.io.TempDir;

class SPPExperimentRunnerTest {
    private static final String HEADER =
            "run,L,C,step,removed_edges,remaining_edges,removed_edge_fraction,"
                    + "largest_cluster_size,largest_cluster_fraction,"
                    + "second_largest_cluster_size,mean_cluster_size,"
                    + "accepted_requests,rejected_requests,seed";

    @TempDir Path temporaryDirectory;

    @Test
    void maxStepsZeroWritesOnlyInitialMeasurement() throws IOException {
        Path path = run(config(2, 2, 1, 0, 5, 42L, temporaryDirectory));

        List<String[]> rows = rows(path);
        assertEquals(1, rows.size());
        assertEquals("0", rows.get(0)[0]);
        assertEquals("0", rows.get(0)[3]);
    }

    @Test
    void oneByOneStructureOnlyRunWritesInitialMeasurement() throws IOException {
        Path path = run(config(1, 1, 1, 0, 1, 42L, temporaryDirectory));

        String[] row = rows(path).get(0);
        assertEquals("0", row[3]);
        assertEquals("0", row[4]);
        assertEquals("0", row[5]);
        assertEquals("0.0", row[6]);
        assertEquals("1", row[7]);
    }

    @Test
    void intervalOneMeasuresEveryStep() throws IOException {
        Path path = run(config(3, 1, 1, 3, 1, 42L, temporaryDirectory));

        assertEquals(List.of(0L, 1L, 2L, 3L), steps(rows(path), 0));
    }

    @Test
    void writesUnalignedFinalStepOnce() throws IOException {
        Path path = run(config(3, 1, 1, 5, 3, 42L, temporaryDirectory));

        List<Long> steps = steps(rows(path), 0);
        assertEquals(List.of(0L, 3L, 5L), steps);
        assertEquals(1, steps.stream().filter(step -> step == 5L).count());
    }

    @Test
    void multipleRunsAreOrderedAndStartFromFreshLattices() throws IOException {
        Path path = run(config(2, 2, 2, 1, 1, 42L, temporaryDirectory));
        List<String[]> rows = rows(path);

        assertArrayEquals(new String[] {"0", "0", "1", "1"},
                rows.stream().map(row -> row[0]).toArray(String[]::new));
        assertEquals(List.of(0L, 1L), steps(rows, 0));
        assertEquals(List.of(0L, 1L), steps(rows, 1));

        for (String[] row : rows) {
            if (row[3].equals("0")) {
                assertEquals("0", row[4]);
                assertEquals("4", row[5]);
                assertEquals("4", row[7]);
            }
        }
    }

    @Test
    void sameConfigurationProducesIdenticalOutput() throws IOException {
        SPPConfig first = config(4, 2, 2, 20, 5, 77L, temporaryDirectory.resolve("first"));
        SPPConfig second = config(4, 2, 2, 20, 5, 77L, temporaryDirectory.resolve("second"));

        String firstOutput = Files.readString(run(first), StandardCharsets.UTF_8);
        String secondOutput = Files.readString(run(second), StandardCharsets.UTF_8);

        assertEquals(firstOutput, secondOutput);
    }

    @Test
    void differentBaseSeedChangesOutput() throws IOException {
        SPPConfig first = config(4, 2, 1, 20, 5, 77L, temporaryDirectory.resolve("first"));
        SPPConfig second = config(4, 2, 1, 20, 5, 78L, temporaryDirectory.resolve("second"));

        String firstOutput = Files.readString(run(first), StandardCharsets.UTF_8);
        String secondOutput = Files.readString(run(second), StandardCharsets.UTF_8);

        assertNotEquals(firstOutput, secondOutput);
    }

    @Test
    void stopsWhenAllEdgesAreRemovedBeforeMaxSteps() throws IOException {
        Path path = run(config(2, 1, 1, 10_000, 50, 42L, temporaryDirectory));
        List<String[]> rows = rows(path);
        String[] last = rows.get(rows.size() - 1);

        assertEquals("0", last[5]);
        assertTrue(Long.parseLong(last[3]) < 10_000L);
    }

    @Test
    void outputHasExpectedHeaderColumnsAndInvariants() throws IOException {
        SPPConfig config = config(3, 2, 2, 7, 3, 42L, temporaryDirectory);
        Path path = run(config);
        List<String> lines = Files.readAllLines(path, StandardCharsets.UTF_8);

        assertEquals(HEADER, lines.get(0));
        long initialEdges = 2L * config.L() * (config.L() - 1L);
        for (String[] row : rows(path)) {
            assertEquals(14, row.length);
            long step = Long.parseLong(row[3]);
            long removed = Long.parseLong(row[4]);
            long remaining = Long.parseLong(row[5]);
            long accepted = Long.parseLong(row[11]);
            long rejected = Long.parseLong(row[12]);
            assertEquals(step, accepted + rejected);
            assertEquals(initialEdges, removed + remaining);
        }
    }

    @Test
    void createModeOverwritesExistingOutput() throws IOException {
        SPPConfig config = config(3, 1, 1, 2, 1, 42L, temporaryDirectory);
        Path path = SPPExperimentRunner.resultPath(config);
        Files.createDirectories(path.getParent());
        Files.writeString(path, "stale data", StandardCharsets.UTF_8);

        run(config);

        assertEquals(HEADER, Files.readAllLines(path, StandardCharsets.UTF_8).get(0));
    }

    @Test
    void rejectsNullConfiguration() {
        assertThrows(IllegalArgumentException.class, () -> new SPPExperimentRunner(null));
        assertThrows(IllegalArgumentException.class, () -> SPPExperimentRunner.resultPath(null));
        assertThrows(IllegalArgumentException.class, () -> SPPExperimentRunner.edgeTracePath(null));
        assertThrows(IllegalArgumentException.class, () -> SPPExperimentRunner.runSummaryPath(null));
    }

    private static Path run(SPPConfig config) throws IOException {
        return new SPPExperimentRunner(config).run();
    }

    private static SPPConfig config(
            int L,
            int C,
            int runs,
            long maxSteps,
            long interval,
            long baseSeed,
            Path outputDirectory) {
        return new SPPConfig(
                L,
                C,
                runs,
                maxSteps,
                interval,
                BoundaryCondition.OPEN,
                baseSeed,
                outputDirectory);
    }

    private static List<String[]> rows(Path path) throws IOException {
        List<String> lines = Files.readAllLines(path, StandardCharsets.UTF_8);
        List<String[]> rows = new ArrayList<>();
        for (int index = 1; index < lines.size(); index++) {
            rows.add(lines.get(index).split(",", -1));
        }
        return rows;
    }

    private static List<Long> steps(List<String[]> rows, int run) {
        return rows.stream()
                .filter(row -> Integer.parseInt(row[0]) == run)
                .map(row -> Long.parseLong(row[3]))
                .toList();
    }
}
