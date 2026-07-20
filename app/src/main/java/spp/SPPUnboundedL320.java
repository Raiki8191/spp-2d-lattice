package spp;

import java.io.IOException;
import java.io.PrintStream;
import java.nio.file.Path;

/** Staged UNBOUNDED L=320 experiment configuration for the v6 analysis. */
public final class SPPUnboundedL320 {
    public static final int L = 320;
    public static final int C = L * L;
    public static final int BENCHMARK_RUNS = 3;
    public static final int PILOT_RUNS = 17;
    public static final long BENCHMARK_BASE_SEED = 3_200_000L;
    public static final long PILOT_BASE_SEED = BENCHMARK_BASE_SEED + BENCHMARK_RUNS;
    public static final Path ROOT = Path.of("out", "unbounded-l320");

    private SPPUnboundedL320() {}

    public static SPPUnboundedL192.Stage benchmarkStage() {
        return new SPPUnboundedL192.Stage(
                "unbounded-l320-benchmark", L, BENCHMARK_RUNS,
                BENCHMARK_BASE_SEED, 1.0, ROOT.resolve("benchmark"));
    }

    public static SPPUnboundedL192.Stage pilotStage() {
        return new SPPUnboundedL192.Stage(
                "unbounded-l320-pilot", L, PILOT_RUNS,
                PILOT_BASE_SEED, 1.0, ROOT.resolve("pilot"));
    }

    public static SPPUnboundedL192.Stage auditStage() {
        return new SPPUnboundedL192.Stage(
                "unbounded-l320-stop-audit", L, BENCHMARK_RUNS,
                BENCHMARK_BASE_SEED, 0.5, ROOT.resolve("stop-audit"));
    }

    public static Path run(SPPUnboundedL192.Stage stage, PrintStream output) throws IOException {
        return SPPUnboundedL192.run(stage, output);
    }
}
