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

/** Runs the pre-production request-level finite-size sweep. */
public final class SPPScalingV1 {
    public static final String TIMING_FILE_NAME = "execution_times.csv";
    private static final int[] LATTICE_SIZES = {8, 12, 16, 24, 32, 48, 64};
    private static final int[] ORDER_CHECK_SIZES = {16, 32, 64};
    private static final int[] FINITE_BUDGETS = {1, 2};
    private static final int[] ORDER_CHECK_BUDGETS = {2};
    private static final int RUNS = 200;
    private static final int ORDER_CHECK_RUNS = 50;
    private static final long BASE_SEED = 42L;

    private SPPScalingV1() {}

    public static Path runDefault(PrintStream output) throws IOException {
        return run(Path.of("out", "scaling-v1"), output, RUNS);
    }

    public static Path runSmoke(PrintStream output) throws IOException {
        return run(Path.of("out", "scaling-v1-smoke"), output, 5);
    }

    public static Path runOrderCheckDefault(PrintStream output) throws IOException {
        return runOrderCheck(Path.of("out", "scaling-v1-order-check"), output);
    }

    public static Path run(Path outputDirectory, PrintStream output, int runs) throws IOException {
        return runPlans(createPlans(LATTICE_SIZES, FINITE_BUDGETS, runs, false, outputDirectory), output);
    }

    public static Path runOrderCheck(Path outputDirectory, PrintStream output) throws IOException {
        return runPlans(
                createPlans(
                        ORDER_CHECK_SIZES,
                        ORDER_CHECK_BUDGETS,
                        ORDER_CHECK_RUNS,
                        true,
                        outputDirectory),
                output);
    }

    public static SPPSweepPlan createPlan(
            int latticeSize,
            int[] finiteBudgets,
            int runs,
            boolean edgeTraceEnabled,
            Path outputDirectory) {
        return new SPPSweepPlan(
                new int[] {latticeSize},
                finiteBudgets,
                true,
                runs,
                SPPPilot.maxStepsForL(latticeSize),
                1,
                MeasurementMode.ACCEPTED_REQUEST,
                RunStopMode.TRANSITION_WINDOW_COMPLETE,
                edgeTraceEnabled,
                BoundaryCondition.OPEN,
                BASE_SEED,
                outputDirectory);
    }

    private static List<SPPSweepPlan> createPlans(
            int[] latticeSizes,
            int[] finiteBudgets,
            int runs,
            boolean edgeTraceEnabled,
            Path outputDirectory) {
        if (outputDirectory == null) {
            throw new IllegalArgumentException("outputDirectory must not be null");
        }
        List<SPPSweepPlan> plans = new ArrayList<>();
        for (int L : latticeSizes) {
            plans.add(createPlan(L, finiteBudgets, runs, edgeTraceEnabled, outputDirectory));
        }
        return List.copyOf(plans);
    }

    private static Path runPlans(List<SPPSweepPlan> plans, PrintStream output)
            throws IOException {
        if (output == null) {
            throw new IllegalArgumentException("output must not be null");
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
            output.println("SPP scaling-v1 conditions=" + conditionCount);
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
        output.println("SPP scaling-v1 completed successfully.");
        return manifest;
    }
}
