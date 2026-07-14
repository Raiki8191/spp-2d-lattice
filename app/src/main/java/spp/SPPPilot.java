package spp;

import java.io.BufferedWriter;
import java.io.IOException;
import java.io.PrintStream;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.StandardOpenOption;
import java.util.ArrayList;
import java.util.List;

/** Runs the fixed, sequential pilot sweep used before larger research experiments. */
public final class SPPPilot {
    public static final String TIMING_FILE_NAME = "execution_times.csv";
    private static final int[] LATTICE_SIZES = {8, 12, 16};
    private static final int[] FINITE_BUDGETS = {1, 2};
    private static final int RUNS = 10;
    private static final long BASE_SEED = 42L;

    private SPPPilot() {}

    public static Path runDefault(PrintStream output) throws IOException {
        return run(Path.of("out", "sweep-pilot"), output);
    }

    public static Path run(Path outputDirectory, PrintStream output) throws IOException {
        if (outputDirectory == null || output == null) {
            throw new IllegalArgumentException("outputDirectory and output must not be null");
        }
        List<SPPSweepPlan> plans = new ArrayList<>();
        for (int L : LATTICE_SIZES) {
            plans.add(createPlan(L, outputDirectory));
        }

        int totalConditions = plans.stream().mapToInt(plan -> plan.conditions().size()).sum();
        output.println("SPP pilot conditions=" + totalConditions);
        Files.createDirectories(outputDirectory);
        Path timingPath = outputDirectory.resolve(TIMING_FILE_NAME);
        try (BufferedWriter timingWriter =
                Files.newBufferedWriter(
                        timingPath,
                        StandardCharsets.UTF_8,
                        StandardOpenOption.CREATE,
                        StandardOpenOption.TRUNCATE_EXISTING,
                        StandardOpenOption.WRITE)) {
            timingWriter.write("condition_index,L,C,budget_mode,max_steps,elapsed_ms");
            timingWriter.newLine();
            int conditionIndex = 0;
            for (SPPSweepPlan plan : plans) {
                for (SPPSweepPlan.Condition condition : plan.conditions()) {
                    output.println(
                            "condition="
                                    + (conditionIndex + 1)
                                    + "/"
                                    + totalConditions
                                    + " L="
                                    + condition.L()
                                    + " C="
                                    + condition.C()
                                    + " budget_mode="
                                    + condition.budgetMode()
                                    + " max_steps="
                                    + plan.maxSteps());
                    long startedAt = System.nanoTime();
                    new SPPExperimentRunner(plan.toConfig(condition)).run();
                    long elapsedMillis = (System.nanoTime() - startedAt) / 1_000_000L;
                    writeTiming(timingWriter, conditionIndex, condition, plan, elapsedMillis);
                    timingWriter.flush();
                    output.println("elapsed_ms=" + elapsedMillis);
                    conditionIndex++;
                }
            }
        }

        Path manifest = SweepManifestWriter.writePlans(outputDirectory, plans);
        output.println("manifest=" + manifest.toAbsolutePath());
        output.println("timings=" + timingPath.toAbsolutePath());
        output.println("SPP pilot completed successfully.");
        return manifest;
    }

    public static SPPSweepPlan createPlan(int L, Path outputDirectory) {
        return new SPPSweepPlan(
                new int[] {L},
                FINITE_BUDGETS,
                true,
                RUNS,
                maxStepsForL(L),
                1,
                MeasurementMode.ACCEPTED_REQUEST,
                BoundaryCondition.OPEN,
                BASE_SEED,
                outputDirectory);
    }

    public static long maxStepsForL(int L) {
        if (L < 1) {
            throw new IllegalArgumentException("L must be at least 1");
        }
        long vertexCount = Math.multiplyExact((long) L, L);
        return Math.multiplyExact(2L, Math.multiplyExact(vertexCount, vertexCount));
    }

    private static void writeTiming(
            BufferedWriter writer,
            int conditionIndex,
            SPPSweepPlan.Condition condition,
            SPPSweepPlan plan,
            long elapsedMillis)
            throws IOException {
        writer.write(Integer.toString(conditionIndex));
        writer.write(',' + Integer.toString(condition.L()));
        writer.write(',' + Integer.toString(condition.C()));
        writer.write(',' + condition.budgetMode().name());
        writer.write(',' + Long.toString(plan.maxSteps()));
        writer.write(',' + Long.toString(elapsedMillis));
        writer.newLine();
    }
}
