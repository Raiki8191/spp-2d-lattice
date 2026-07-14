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

/** Runs the bounded L=24,32 scaling benchmark without changing simulation semantics. */
public final class SPPScalingBenchmark {
    public static final String TIMING_FILE_NAME = "execution_times.csv";
    private static final int[] LATTICE_SIZES = {24, 32};
    private static final int[] FINITE_BUDGETS = {1, 2};
    private static final int RUNS = 3;
    private static final long BASE_SEED = 42L;

    private SPPScalingBenchmark() {}

    public static Path runDefault(PrintStream output) throws IOException {
        return run(Path.of("out", "scaling-benchmark"), output);
    }

    public static Path run(Path outputDirectory, PrintStream output) throws IOException {
        if (outputDirectory == null || output == null) {
            throw new IllegalArgumentException("outputDirectory and output must not be null");
        }
        List<SPPSweepPlan> plans = new ArrayList<>();
        for (int latticeSize : LATTICE_SIZES) {
            plans.add(createPlan(latticeSize, outputDirectory));
        }

        int conditionCount = plans.stream().mapToInt(plan -> plan.conditions().size()).sum();
        Files.createDirectories(outputDirectory);
        Path timingPath = outputDirectory.resolve(TIMING_FILE_NAME);
        try (BufferedWriter writer =
                Files.newBufferedWriter(
                        timingPath,
                        StandardCharsets.UTF_8,
                        StandardOpenOption.CREATE,
                        StandardOpenOption.TRUNCATE_EXISTING,
                        StandardOpenOption.WRITE)) {
            writer.write("condition_index,L,C,budget_mode,max_steps,elapsed_ms");
            writer.newLine();
            int conditionIndex = 0;
            output.println("SPP scaling benchmark conditions=" + conditionCount);
            for (SPPSweepPlan plan : plans) {
                for (SPPSweepPlan.Condition condition : plan.conditions()) {
                    long startedAt = System.nanoTime();
                    new SPPExperimentRunner(plan.toConfig(condition)).run();
                    long elapsedMillis = (System.nanoTime() - startedAt) / 1_000_000L;
                    writeTiming(writer, conditionIndex, condition, plan, elapsedMillis);
                    writer.flush();
                    output.println(
                            "condition="
                                    + conditionIndex
                                    + " L="
                                    + condition.L()
                                    + " C="
                                    + condition.C()
                                    + " budget_mode="
                                    + condition.budgetMode()
                                    + " elapsed_ms="
                                    + elapsedMillis);
                    conditionIndex++;
                }
            }
        }
        Path manifest = SweepManifestWriter.writePlans(outputDirectory, plans);
        output.println("manifest=" + manifest.toAbsolutePath());
        output.println("timings=" + timingPath.toAbsolutePath());
        output.println("SPP scaling benchmark completed successfully.");
        return manifest;
    }

    public static SPPSweepPlan createPlan(int latticeSize, Path outputDirectory) {
        return new SPPSweepPlan(
                new int[] {latticeSize},
                FINITE_BUDGETS,
                true,
                RUNS,
                SPPPilot.maxStepsForL(latticeSize),
                1,
                MeasurementMode.ACCEPTED_REQUEST,
                BoundaryCondition.OPEN,
                BASE_SEED,
                outputDirectory);
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
