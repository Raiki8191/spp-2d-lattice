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

/** Runs the L=96,128 scaling-v2 production and stop-audit sweeps. */
public final class SPPScalingV2 {
    public static final String TIMING_FILE_NAME = "execution_times.csv";
    public static final Path MAIN_OUTPUT = Path.of("out", "scaling-v2-main");
    public static final Path AUDIT_OUTPUT = Path.of("out", "scaling-v2-stop-audit");
    private static final int[] LATTICE_SIZES = {96, 128};
    private static final int FINITE_RUNS = 200;
    private static final int UNBOUNDED_RUNS = 400;
    private static final int AUDIT_RUNS = 20;
    private static final long BASE_SEED = 42L;

    private SPPScalingV2() {}

    public static Path runMain(PrintStream output) throws IOException {
        return runPlans(createMainPlans(MAIN_OUTPUT), output, "scaling-v2 main");
    }

    public static Path runStopAudit(PrintStream output) throws IOException {
        return runPlans(createStopAuditPlans(AUDIT_OUTPUT), output, "scaling-v2 stop audit");
    }

    public static Path runSmoke(PrintStream output) throws IOException {
        Path outputDirectory = Path.of("out", "scaling-v2-main-smoke");
        // L=10 avoids overlapping the persisted scaling-v1 production sizes.
        return runPlans(createPlans(new int[] {10}, 2, 3, 1.0, outputDirectory), output,
                "scaling-v2 main smoke");
    }

    public static List<SPPSweepPlan> createMainPlans(Path outputDirectory) {
        return createPlans(LATTICE_SIZES, FINITE_RUNS, UNBOUNDED_RUNS, 1.0,
                outputDirectory);
    }

    public static List<SPPSweepPlan> createStopAuditPlans(Path outputDirectory) {
        return createPlans(LATTICE_SIZES, AUDIT_RUNS, AUDIT_RUNS, 0.5,
                outputDirectory);
    }

    static List<SPPSweepPlan> createPlans(
            int[] latticeSizes,
            int finiteRuns,
            int unboundedRuns,
            double thresholdMultiplier,
            Path outputDirectory) {
        if (latticeSizes == null || outputDirectory == null) {
            throw new IllegalArgumentException("latticeSizes and outputDirectory are required");
        }
        List<SPPSweepPlan> plans = new ArrayList<>();
        for (int L : latticeSizes) {
            plans.add(createPlan(L, new int[] {1}, false, finiteRuns,
                    thresholdMultiplier, outputDirectory));
            plans.add(createPlan(L, new int[] {2}, false, finiteRuns,
                    thresholdMultiplier, outputDirectory));
            plans.add(createPlan(L, new int[0], true, unboundedRuns,
                    thresholdMultiplier, outputDirectory));
        }
        return List.copyOf(plans);
    }

    private static SPPSweepPlan createPlan(
            int L,
            int[] finiteBudgets,
            boolean includeUnbounded,
            int runs,
            double thresholdMultiplier,
            Path outputDirectory) {
        return new SPPSweepPlan(
                new int[] {L},
                finiteBudgets,
                includeUnbounded,
                runs,
                SPPPilot.maxStepsForL(L),
                1,
                MeasurementMode.ACCEPTED_REQUEST,
                RunStopMode.TRANSITION_WINDOW_COMPLETE,
                thresholdMultiplier,
                false,
                BoundaryCondition.OPEN,
                BASE_SEED,
                outputDirectory);
    }

    static Path runPlans(List<SPPSweepPlan> plans, PrintStream output, String label)
            throws IOException {
        if (plans == null || plans.isEmpty() || output == null) {
            throw new IllegalArgumentException("non-empty plans and output are required");
        }
        Path outputDirectory = plans.get(0).outputDirectory();
        Files.createDirectories(outputDirectory);
        Path timingPath = outputDirectory.resolve(TIMING_FILE_NAME);
        int conditionCount = plans.stream().mapToInt(plan -> plan.conditions().size()).sum();
        try (BufferedWriter writer = Files.newBufferedWriter(
                timingPath,
                StandardCharsets.UTF_8,
                StandardOpenOption.CREATE,
                StandardOpenOption.TRUNCATE_EXISTING,
                StandardOpenOption.WRITE)) {
            writer.write("condition_index,L,C,budget_mode,runs,max_steps,elapsed_ms");
            writer.newLine();
            int conditionIndex = 0;
            output.println("SPP " + label + " conditions=" + conditionCount);
            for (SPPSweepPlan plan : plans) {
                for (SPPSweepPlan.Condition condition : plan.conditions()) {
                    long startedAt = System.nanoTime();
                    new SPPExperimentRunner(plan.toConfig(condition)).run();
                    long elapsedMillis = (System.nanoTime() - startedAt) / 1_000_000L;
                    writer.write(conditionIndex + "," + condition.L() + "," + condition.C()
                            + "," + condition.budgetMode().name() + "," + plan.runs()
                            + "," + plan.maxSteps() + "," + elapsedMillis);
                    writer.newLine();
                    writer.flush();
                    output.println("condition=" + conditionIndex + " L=" + condition.L()
                            + " C=" + condition.C() + " budget_mode="
                            + condition.budgetMode() + " runs=" + plan.runs()
                            + " elapsed_ms=" + elapsedMillis);
                    conditionIndex++;
                }
            }
        }
        Path manifest = SweepManifestWriter.writePlans(outputDirectory, plans);
        output.println("manifest=" + manifest.toAbsolutePath());
        output.println("timings=" + timingPath.toAbsolutePath());
        output.println("SPP " + label + " completed successfully.");
        return manifest;
    }
}
