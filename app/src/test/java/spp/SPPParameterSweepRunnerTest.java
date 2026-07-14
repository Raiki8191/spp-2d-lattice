package spp;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertNotEquals;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.junit.jupiter.api.Assertions.assertTrue;

import java.io.ByteArrayOutputStream;
import java.io.IOException;
import java.io.PrintStream;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.io.TempDir;

class SPPParameterSweepRunnerTest {
    @TempDir Path temporaryDirectory;

    @Test
    void writesEveryResultAndOrderedManifestWithoutOverwritingConditions() throws IOException {
        Path root = temporaryDirectory.resolve("sweep");
        SPPSweepPlan plan = plan(root, new int[] {3, 2}, new int[] {1}, true, 2, 5);

        Path manifest = runQuietly(plan);

        assertEquals(root.resolve("manifest.csv"), manifest);
        List<String> manifestLines = Files.readAllLines(manifest, StandardCharsets.UTF_8);
        assertEquals(1 + plan.conditions().size(), manifestLines.size());
        assertEquals(SweepManifestWriter.HEADER, manifestLines.get(0));
        assertTrue(manifestLines.get(1).contains("0,2,1,FINITE"));
        assertTrue(manifestLines.get(2).contains("1,2,4,UNBOUNDED"));
        assertTrue(manifestLines.get(3).contains("2,3,1,FINITE"));
        assertTrue(manifestLines.get(4).contains("3,3,9,UNBOUNDED"));

        for (SPPSweepPlan.Condition condition : plan.conditions()) {
            Path result = resultPath(root, condition.L(), condition.C());
            assertTrue(Files.isRegularFile(result));
            List<String> lines = Files.readAllLines(result, StandardCharsets.UTF_8);
            assertEquals(CsvWriter.HEADER, lines.get(0));
            assertTrue(lines.stream().skip(1).allMatch(line -> line.split(",", -1).length == 14));
            assertEquals(List.of(0, 1), distinctRuns(lines));
        }
    }

    @Test
    void identicalPlansInSeparateDirectoriesAreReproducible() throws IOException {
        Path firstRoot = temporaryDirectory.resolve("first");
        Path secondRoot = temporaryDirectory.resolve("second");
        SPPSweepPlan first = plan(firstRoot, new int[] {3}, new int[] {1, 2}, true, 2, 8);
        SPPSweepPlan second = plan(secondRoot, new int[] {3}, new int[] {1, 2}, true, 2, 8);

        runQuietly(first);
        runQuietly(second);

        assertEquals(
                Files.readString(firstRoot.resolve("manifest.csv")),
                Files.readString(secondRoot.resolve("manifest.csv")));
        for (SPPSweepPlan.Condition condition : first.conditions()) {
            assertEquals(
                    Files.readString(resultPath(firstRoot, condition.L(), condition.C())),
                    Files.readString(resultPath(secondRoot, condition.L(), condition.C())));
        }
    }

    @Test
    void sameLAndRunUseSameSeedForDifferentBudgets() throws IOException {
        Path root = temporaryDirectory.resolve("seeds");
        SPPSweepPlan plan = plan(root, new int[] {4}, new int[] {1, 2}, true, 2, 4);
        runQuietly(plan);

        Map<Integer, Long> expectedSeeds = seedsByRun(resultPath(root, 4, 1));
        assertEquals(expectedSeeds, seedsByRun(resultPath(root, 4, 2)));
        assertEquals(expectedSeeds, seedsByRun(resultPath(root, 4, 16)));
        assertNotEquals(expectedSeeds.get(0), expectedSeeds.get(1));
    }

    @Test
    void manifestContainsOnlyOneCollapsedUnboundedCondition() throws IOException {
        Path root = temporaryDirectory.resolve("collapsed-manifest");
        SPPSweepPlan plan =
                plan(root, new int[] {4}, new int[] {2, 15, 16, 20}, false, 1, 0);

        Path manifest = runQuietly(plan);
        List<String> lines = Files.readAllLines(manifest, StandardCharsets.UTF_8);

        assertEquals(3, lines.size());
        assertTrue(lines.get(1).contains("0,4,2,FINITE"));
        assertTrue(lines.get(2).contains("1,4,16,UNBOUNDED"));
        assertEquals(2, lines.stream().skip(1).distinct().count());
    }

    @Test
    void rejectsNullInputs() {
        assertThrows(IllegalArgumentException.class, () -> new SPPParameterSweepRunner(null));
        SPPParameterSweepRunner runner =
                new SPPParameterSweepRunner(
                        plan(temporaryDirectory, new int[] {2}, new int[] {1}, false, 1, 0));
        assertThrows(IllegalArgumentException.class, () -> runner.run(null));
        assertThrows(IllegalArgumentException.class, () -> SweepManifestWriter.write(null));
    }

    private static Path runQuietly(SPPSweepPlan plan) throws IOException {
        try (PrintStream output =
                new PrintStream(new ByteArrayOutputStream(), true, StandardCharsets.UTF_8)) {
            return new SPPParameterSweepRunner(plan).run(output);
        }
    }

    private static SPPSweepPlan plan(
            Path root, int[] sizes, int[] budgets, boolean unbounded, int runs, long maxSteps) {
        return new SPPSweepPlan(
                sizes,
                budgets,
                unbounded,
                runs,
                maxSteps,
                2,
                MeasurementMode.ACCEPTED_REQUEST,
                BoundaryCondition.OPEN,
                42,
                root);
    }

    private static Path resultPath(Path root, int L, int C) {
        return root.resolve("L=" + L).resolve("C=" + C).resolve("results.csv");
    }

    private static List<Integer> distinctRuns(List<String> lines) {
        return lines.stream()
                .skip(1)
                .map(line -> Integer.parseInt(line.split(",", -1)[0]))
                .distinct()
                .toList();
    }

    private static Map<Integer, Long> seedsByRun(Path result) throws IOException {
        Map<Integer, Long> seeds = new HashMap<>();
        List<String> lines = Files.readAllLines(result, StandardCharsets.UTF_8);
        for (String line : lines.subList(1, lines.size())) {
            String[] fields = line.split(",", -1);
            seeds.putIfAbsent(Integer.parseInt(fields[0]), Long.parseLong(fields[13]));
        }
        return seeds;
    }
}
