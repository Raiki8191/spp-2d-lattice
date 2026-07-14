package spp;

import java.io.IOException;
import java.io.PrintStream;
import java.nio.file.Path;
import java.util.List;

/** Executes all conditions in an {@link SPPSweepPlan} sequentially. */
public final class SPPParameterSweepRunner {
    private final SPPSweepPlan plan;

    public SPPParameterSweepRunner(SPPSweepPlan plan) {
        if (plan == null) {
            throw new IllegalArgumentException("plan must not be null");
        }
        this.plan = plan;
    }

    public Path run() throws IOException {
        return run(System.out);
    }

    public Path run(PrintStream output) throws IOException {
        if (output == null) {
            throw new IllegalArgumentException("output must not be null");
        }
        List<SPPSweepPlan.Condition> conditions = plan.conditions();
        long startedAt = System.nanoTime();
        output.println("SPP sweep conditions=" + conditions.size());
        for (SPPSweepPlan.Condition condition : conditions) {
            output.println(
                    "condition="
                            + (condition.conditionIndex() + 1)
                            + "/"
                            + conditions.size()
                            + " L="
                            + condition.L()
                            + " C="
                            + condition.C()
                            + " budget_mode="
                            + condition.budgetMode());
            new SPPExperimentRunner(plan.toConfig(condition)).run();
        }
        Path manifest = SweepManifestWriter.write(plan);
        long elapsedMillis = (System.nanoTime() - startedAt) / 1_000_000L;
        output.println("manifest=" + manifest.toAbsolutePath());
        output.println("elapsed_ms=" + elapsedMillis);
        output.println("SPP parameter sweep completed successfully.");
        return manifest;
    }
}
