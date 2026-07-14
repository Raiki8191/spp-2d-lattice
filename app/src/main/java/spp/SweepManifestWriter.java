package spp;

import java.io.BufferedWriter;
import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.StandardOpenOption;

/** Writes the machine-readable manifest for a completed parameter sweep. */
public final class SweepManifestWriter {
    public static final String HEADER =
            "condition_index,L,C,budget_mode,runs,max_steps,measurement_mode,"
                    + "measurement_interval,base_seed,result_path";
    public static final String FILE_NAME = "manifest.csv";

    private SweepManifestWriter() {}

    public static Path write(SPPSweepPlan plan) throws IOException {
        if (plan == null) {
            throw new IllegalArgumentException("plan must not be null");
        }
        Path manifest = plan.outputDirectory().resolve(FILE_NAME);
        Files.createDirectories(plan.outputDirectory());
        try (BufferedWriter writer =
                Files.newBufferedWriter(
                        manifest,
                        StandardCharsets.UTF_8,
                        StandardOpenOption.CREATE,
                        StandardOpenOption.TRUNCATE_EXISTING,
                        StandardOpenOption.WRITE)) {
            writer.write(HEADER);
            writer.newLine();
            for (SPPSweepPlan.Condition condition : plan.conditions()) {
                writeCondition(writer, plan, condition);
            }
        }
        return manifest;
    }

    private static void writeCondition(
            BufferedWriter writer, SPPSweepPlan plan, SPPSweepPlan.Condition condition)
            throws IOException {
        String relativeResultPath =
                "L=" + condition.L() + "/C=" + condition.C() + "/results.csv";
        writer.write(Integer.toString(condition.conditionIndex()));
        writer.write(',' + Integer.toString(condition.L()));
        writer.write(',' + Integer.toString(condition.C()));
        writer.write(',' + condition.budgetMode().name());
        writer.write(',' + Integer.toString(plan.runs()));
        writer.write(',' + Long.toString(plan.maxSteps()));
        writer.write(',' + plan.measurementMode().name());
        writer.write(',' + Long.toString(plan.measurementInterval()));
        writer.write(',' + Long.toString(plan.baseSeed()));
        writer.write(',' + relativeResultPath);
        writer.newLine();
    }
}
