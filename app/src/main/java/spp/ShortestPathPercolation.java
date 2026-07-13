package spp;

import java.io.IOException;
import java.io.PrintStream;
import java.nio.file.Path;

/** Application entry point for a small, deterministic SPP experiment. */
public final class ShortestPathPercolation {
    private ShortestPathPercolation() {}

    public static void main(String[] args) throws IOException {
        run(createDefaultConfig(), System.out);
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
