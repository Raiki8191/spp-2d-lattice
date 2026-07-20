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

/** Runs the bounded L=96,128 transition-extension benchmark for scaling-v2 planning. */
public final class SPPScalingV2Benchmark {
    public static final String TIMING_FILE_NAME = "execution_times.csv";
    public static final double THRESHOLD_MULTIPLIER = 0.5;
    private static final int[] LATTICE_SIZES = {96, 128};
    private static final int[] FINITE_BUDGETS = {1, 2};
    private static final int RUNS = 5;
    private static final long BASE_SEED = 42L;

    private SPPScalingV2Benchmark() {}

    public static Path runDefault(PrintStream output) throws IOException {
        return run(Path.of("out", "scaling-v2-benchmark"), output);
    }

    public static Path runSmoke(PrintStream output) throws IOException {
        return runPlans(
                List.of(createPlan(8, 2, Path.of("out", "scaling-v2-benchmark-smoke"))),
                output);
    }

    public static Path run(Path outputDirectory, PrintStream output) throws IOException {
        if (outputDirectory == null) {
            throw new IllegalArgumentException("outputDirectory must not be null");
        }
        List<SPPSweepPlan> plans = new ArrayList<>();
        for (int latticeSize : LATTICE_SIZES) {
            plans.add(createPlan(latticeSize, RUNS, outputDirectory));
        }
        return runPlans(plans, output);
    }

    public static SPPSweepPlan createPlan(int latticeSize, int runs, Path outputDirectory) {
        return new SPPSweepPlan(
                new int[] {latticeSize},
                FINITE_BUDGETS,
                true,
                runs,
                SPPPilot.maxStepsForL(latticeSize),
                1,
                MeasurementMode.ACCEPTED_REQUEST,
                RunStopMode.TRANSITION_WINDOW_COMPLETE,
                THRESHOLD_MULTIPLIER,
                false,
                BoundaryCondition.OPEN,
                BASE_SEED,
                outputDirectory);
    }

    private static Path runPlans(List<SPPSweepPlan> plans, PrintStream output)
            throws IOException {
        if (plans == null || plans.isEmpty() || output == null) {
            throw new IllegalArgumentException("non-empty plans and output are required");
        }
        Path outputDirectory = plans.get(0).outputDirectory();
        Files.createDirectories(outputDirectory);
        Path timingPath = outputDirectory.resolve(TIMING_FILE_NAME);
        int conditionCount = plans.stream().mapToInt(plan -> plan.conditions().size()).sum();
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
            output.println("SPP scaling-v2 benchmark conditions=" + conditionCount);
            for (SPPSweepPlan plan : plans) {
                for (SPPSweepPlan.Condition condition : plan.conditions()) {
                    long startedAt = System.nanoTime();
                    new SPPExperimentRunner(plan.toConfig(condition)).run();
                    long elapsedMillis = (System.nanoTime() - startedAt) / 1_000_000L;
                    writer.write(
                            conditionIndex
                                    + ","
                                    + condition.L()
                                    + ","
                                    + condition.C()
                                    + ","
                                    + condition.budgetMode().name()
                                    + ","
                                    + plan.maxSteps()
                                    + ","
                                    + elapsedMillis);
                    writer.newLine();
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
        output.println("SPP scaling-v2 benchmark completed successfully.");
        return manifest;
    }
}
