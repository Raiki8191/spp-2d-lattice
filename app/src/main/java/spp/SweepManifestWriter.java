package spp;

import java.io.BufferedWriter;
import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.StandardOpenOption;
import java.util.HashSet;
import java.util.List;
import java.util.Set;

/** Writes the machine-readable manifest for a completed parameter sweep. */
public final class SweepManifestWriter {
    public static final String HEADER =
            "condition_index,L,C,budget_mode,runs,max_steps,measurement_mode,"
                    + "measurement_interval,base_seed,result_path,stop_mode,"
                    + "transition_threshold_multiplier,edge_trace_path";
    public static final String HEADER_WITHOUT_EDGE_TRACE =
            "condition_index,L,C,budget_mode,runs,max_steps,measurement_mode,"
                    + "measurement_interval,base_seed,result_path,stop_mode,"
                    + "transition_threshold_multiplier";
    public static final String FILE_NAME = "manifest.csv";

    private SweepManifestWriter() {}

    public static Path write(SPPSweepPlan plan) throws IOException {
        if (plan == null) {
            throw new IllegalArgumentException("plan must not be null");
        }
        return writePlans(plan.outputDirectory(), List.of(plan));
    }

    /** Writes one manifest for several per-L plans with globally unique condition indices. */
    public static Path writePlans(Path outputDirectory, List<SPPSweepPlan> plans)
            throws IOException {
        if (outputDirectory == null || plans == null || plans.isEmpty()) {
            throw new IllegalArgumentException("outputDirectory and non-empty plans are required");
        }
        Path manifest = outputDirectory.resolve(FILE_NAME);
        Files.createDirectories(outputDirectory);
        if (plans.get(0) == null) {
            throw new IllegalArgumentException("plans must not contain null");
        }
        boolean edgeTraceEnabled = plans.get(0).edgeTraceEnabled();
        if (plans.stream()
                .anyMatch(plan -> plan == null || plan.edgeTraceEnabled() != edgeTraceEnabled)) {
            throw new IllegalArgumentException(
                    "all plans in one manifest must use the same edge trace setting");
        }
        try (BufferedWriter writer =
                Files.newBufferedWriter(
                        manifest,
                        StandardCharsets.UTF_8,
                        StandardOpenOption.CREATE,
                        StandardOpenOption.TRUNCATE_EXISTING,
                        StandardOpenOption.WRITE)) {
            writer.write(edgeTraceEnabled ? HEADER : HEADER_WITHOUT_EDGE_TRACE);
            writer.newLine();
            int conditionIndex = 0;
            Set<String> conditionKeys = new HashSet<>();
            for (SPPSweepPlan plan : plans) {
                if (plan == null || !plan.outputDirectory().equals(outputDirectory)) {
                    throw new IllegalArgumentException(
                            "every plan must use the supplied outputDirectory");
                }
                for (SPPSweepPlan.Condition condition : plan.conditions()) {
                    String conditionKey = condition.L() + ":" + condition.C();
                    if (!conditionKeys.add(conditionKey)) {
                        throw new IllegalArgumentException(
                                "duplicate sweep condition: L="
                                        + condition.L()
                                        + ", C="
                                        + condition.C());
                    }
                    writeCondition(writer, plan, condition, conditionIndex++, edgeTraceEnabled);
                }
            }
        }
        return manifest;
    }

    private static void writeCondition(
            BufferedWriter writer,
            SPPSweepPlan plan,
            SPPSweepPlan.Condition condition,
            int conditionIndex,
            boolean edgeTraceEnabled)
            throws IOException {
        String relativeResultPath =
                "L=" + condition.L() + "/C=" + condition.C() + "/results.csv";
        String relativeEdgeTracePath =
                "L=" + condition.L() + "/C=" + condition.C() + "/edge_removals.csv";
        writer.write(Integer.toString(conditionIndex));
        writer.write(',' + Integer.toString(condition.L()));
        writer.write(',' + Integer.toString(condition.C()));
        writer.write(',' + condition.budgetMode().name());
        writer.write(',' + Integer.toString(plan.runs()));
        writer.write(',' + Long.toString(plan.maxSteps()));
        writer.write(',' + plan.measurementMode().name());
        writer.write(',' + Long.toString(plan.measurementInterval()));
        writer.write(',' + Long.toString(plan.baseSeed()));
        writer.write(',' + relativeResultPath);
        writer.write(',' + plan.stopMode().name());
        writer.write(',' + Double.toString(plan.transitionThresholdMultiplier()));
        if (edgeTraceEnabled) {
            writer.write(',' + relativeEdgeTracePath);
        }
        writer.newLine();
    }
}
