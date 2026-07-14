package spp;

import java.io.IOException;
import java.io.PrintStream;
import java.nio.file.Path;

/** Application entry point for a small, deterministic SPP parameter sweep. */
public final class ShortestPathPercolation {
    private ShortestPathPercolation() {}

    public static void main(String[] args) throws IOException {
        if (args.length == 1 && "--pilot".equals(args[0])) {
            SPPPilot.runDefault(System.out);
            return;
        }
        if (args.length == 1 && "--scaling-benchmark".equals(args[0])) {
            SPPScalingBenchmark.runDefault(System.out);
            return;
        }
        if (args.length == 1 && "--scaling-benchmark-large".equals(args[0])) {
            SPPScalingBenchmark.runLargeDefault(System.out);
            return;
        }
        if (args.length == 1 && "--scaling-v1".equals(args[0])) {
            SPPScalingV1.runDefault(System.out);
            return;
        }
        if (args.length == 1 && "--scaling-v1-smoke".equals(args[0])) {
            SPPScalingV1.runSmoke(System.out);
            return;
        }
        if (args.length == 1 && "--scaling-v1-order-check".equals(args[0])) {
            SPPScalingV1.runOrderCheckDefault(System.out);
            return;
        }
        if (args.length != 0) {
            throw new IllegalArgumentException(
                    "supported arguments: --pilot, --scaling-benchmark, "
                            + "--scaling-benchmark-large, --scaling-v1, "
                            + "--scaling-v1-smoke, --scaling-v1-order-check");
        }
        new SPPParameterSweepRunner(createSmokeSweepPlan()).run(System.out);
    }

    public static SPPSweepPlan createSmokeSweepPlan() {
        return new SPPSweepPlan(
                new int[] {4, 6},
                new int[] {1, 2},
                true,
                2,
                20,
                5,
                MeasurementMode.ACCEPTED_REQUEST,
                BoundaryCondition.OPEN,
                42L,
                Path.of("out", "sweep-smoke"));
    }

    public static SPPConfig createDefaultConfig() {
        return new SPPConfig(
                4,
                2,
                2,
                20,
                5,
                BoundaryCondition.OPEN,
                42L,
                Path.of("out", "spp"));
    }

    /** Runs one configured batch and prints a concise completion summary. */
    public static Path run(SPPConfig config, PrintStream output) throws IOException {
        if (config == null) {
            throw new IllegalArgumentException("config must not be null");
        }
        if (output == null) {
            throw new IllegalArgumentException("output must not be null");
        }

        Path outputPath = new SPPExperimentRunner(config).run();
        output.println("L=" + config.L());
        output.println("C=" + config.C());
        output.println("runs=" + config.runs());
        output.println("output=" + outputPath.toAbsolutePath());
        output.println("SPP experiment completed successfully.");
        return outputPath;
    }
}
