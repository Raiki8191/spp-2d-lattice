package spp;

import java.io.IOException;
import java.io.UncheckedIOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.Random;
import java.util.random.RandomGenerator;

/** Runs a configured batch sequentially and writes configured measurements to one CSV file. */
public final class SPPExperimentRunner {
    private static final String RESULT_FILE_NAME = "results.csv";
    private static final String EDGE_TRACE_FILE_NAME = "edge_removals.csv";
    private static final String RUN_SUMMARY_FILE_NAME = "run_summary.csv";

    private final SPPConfig config;
    private final Path outputPath;
    private final Path edgeTracePath;
    private final Path runSummaryPath;

    public SPPExperimentRunner(SPPConfig config) {
        if (config == null) {
            throw new IllegalArgumentException("config must not be null");
        }
        this.config = config;
        this.outputPath = resultPath(config);
        this.edgeTracePath = edgeTracePath(config);
        this.runSummaryPath = runSummaryPath(config);
    }

    /**
     * Executes every run sequentially. The output file is deliberately replaced rather than
     * appended because resume and append modes are outside the initial implementation.
     *
     * @return the CSV file written by this execution
     */
    public Path run() throws IOException {
        ClusterAnalyzer clusterAnalyzer = new ClusterAnalyzer();
        if (!config.edgeTraceEnabled()) {
            Files.deleteIfExists(edgeTracePath);
        }
        EdgeRemovalTraceWriter traceWriter =
                config.edgeTraceEnabled() ? EdgeRemovalTraceWriter.create(edgeTracePath) : null;
        try (CsvWriter csvWriter = CsvWriter.create(outputPath);
                EdgeRemovalTraceWriter closeableTraceWriter = traceWriter;
                RunSummaryWriter summaryWriter = RunSummaryWriter.create(runSummaryPath)) {
            for (int run = 0; run < config.runs(); run++) {
                executeRun(run, clusterAnalyzer, csvWriter, traceWriter, summaryWriter);
            }
        } catch (UncheckedIOException error) {
            throw error.getCause();
        }
        return outputPath;
    }

    public Path outputPath() {
        return outputPath;
    }

    public Path edgeTracePath() {
        return edgeTracePath;
    }

    public Path runSummaryPath() {
        return runSummaryPath;
    }

    public static Path resultPath(SPPConfig config) {
        if (config == null) {
            throw new IllegalArgumentException("config must not be null");
        }
        return config.outputDirectory()
                .resolve("L=" + config.L())
                .resolve("C=" + config.C())
                .resolve(RESULT_FILE_NAME);
    }

    public static Path edgeTracePath(SPPConfig config) {
        if (config == null) {
            throw new IllegalArgumentException("config must not be null");
        }
        return config.outputDirectory()
                .resolve("L=" + config.L())
                .resolve("C=" + config.C())
                .resolve(EDGE_TRACE_FILE_NAME);
    }

    public static Path runSummaryPath(SPPConfig config) {
        if (config == null) {
            throw new IllegalArgumentException("config must not be null");
        }
        return config.outputDirectory()
                .resolve("L=" + config.L())
                .resolve("C=" + config.C())
                .resolve(RUN_SUMMARY_FILE_NAME);
    }

    private void executeRun(
            int run,
            ClusterAnalyzer clusterAnalyzer,
            CsvWriter csvWriter,
            EdgeRemovalTraceWriter traceWriter,
            RunSummaryWriter summaryWriter)
            throws IOException {
        long startedAt = System.nanoTime();
        SquareLattice lattice = new SquareLattice(config.L());
        long runSeed = SeedUtils.runSeed(config.baseSeed(), run);

        // L=1 with maxSteps=0 is a valid structure-only experiment but cannot construct a
        // request processor, which requires two distinct vertices.
        if (lattice.vertexCount() < 2) {
            ClusterStats initialStats = clusterAnalyzer.analyze(lattice);
            csvWriter.write(initialResult(run, runSeed, lattice, initialStats));
            writeSummary(
                    summaryWriter,
                    run,
                    runSeed,
                    lattice,
                    0L,
                    initialStats,
                    TerminationReason.ALL_EDGES_REMOVED,
                    startedAt);
            return;
        }

        RandomGenerator pairRandom = new Random(SeedUtils.pairSeed(runSeed));
        RandomGenerator pathRandom = new Random(SeedUtils.pathSeed(runSeed));
        SPPSimulator simulator =
                new SPPSimulator(
                        lattice,
                        config.C(),
                        pairRandom,
                        pathRandom,
                        traceWriter == null
                                ? EdgeRemovalObserver.NONE
                                : traceWriter.observerForRun(run, runSeed));

        ClusterStats finalStats =
                writeMeasurement(run, runSeed, lattice, simulator, clusterAnalyzer, csvWriter);
        long lastMeasuredStep = 0L;
        boolean transitionWindowComplete = false;

        while (simulator.getStep() < config.maxSteps() && lattice.remainingEdgeCount() > 0) {
            SPPStepResult stepResult = simulator.step();
            if (shouldMeasure(stepResult)) {
                finalStats =
                        writeMeasurement(
                                run, runSeed, lattice, simulator, clusterAnalyzer, csvWriter);
                lastMeasuredStep = simulator.getStep();
                transitionWindowComplete =
                        config.stopMode() == RunStopMode.TRANSITION_WINDOW_COMPLETE
                                && stepResult.accepted()
                                && largestClusterFraction(finalStats, lattice) <= 1.0 / config.L();
                if (transitionWindowComplete) {
                    break;
                }
            }
        }

        if (simulator.getStep() != lastMeasuredStep) {
            finalStats =
                    writeMeasurement(run, runSeed, lattice, simulator, clusterAnalyzer, csvWriter);
        }
        TerminationReason terminationReason =
                terminationReason(lattice, transitionWindowComplete);
        writeSummary(
                summaryWriter,
                run,
                runSeed,
                lattice,
                simulator.getStep(),
                finalStats,
                terminationReason,
                startedAt);
    }

    private boolean shouldMeasure(SPPStepResult stepResult) {
        return switch (config.measurementMode()) {
            case STEP_INTERVAL -> stepResult.step() % config.measurementInterval() == 0;
            case ACCEPTED_REQUEST -> stepResult.accepted();
        };
    }

    private ClusterStats writeMeasurement(
            int run,
            long runSeed,
            SquareLattice lattice,
            SPPSimulator simulator,
            ClusterAnalyzer clusterAnalyzer,
            CsvWriter csvWriter)
            throws IOException {
        ClusterStats clusterStats = clusterAnalyzer.analyze(lattice);
        csvWriter.write(
                SPPResult.capture(
                        run,
                        config.L(),
                        config.C(),
                        runSeed,
                        lattice,
                        simulator,
                        clusterStats));
        return clusterStats;
    }

    private TerminationReason terminationReason(
            SquareLattice lattice, boolean transitionWindowComplete) {
        if (lattice.remainingEdgeCount() == 0) {
            return TerminationReason.ALL_EDGES_REMOVED;
        }
        if (transitionWindowComplete) {
            return TerminationReason.TRANSITION_WINDOW_COMPLETE;
        }
        return TerminationReason.MAX_STEPS;
    }

    private void writeSummary(
            RunSummaryWriter summaryWriter,
            int run,
            long runSeed,
            SquareLattice lattice,
            long finalStep,
            ClusterStats finalStats,
            TerminationReason terminationReason,
            long startedAt)
            throws IOException {
        summaryWriter.write(
                run,
                runSeed,
                finalStep,
                lattice.removedEdgeCount(),
                lattice.initialEdgeCount() == 0
                        ? 0.0
                        : (double) lattice.removedEdgeCount() / lattice.initialEdgeCount(),
                largestClusterFraction(finalStats, lattice),
                terminationReason,
                (System.nanoTime() - startedAt) / 1_000_000L);
    }

    private double largestClusterFraction(ClusterStats stats, SquareLattice lattice) {
        return (double) stats.largestClusterSize() / lattice.vertexCount();
    }

    private SPPResult initialResult(
            int run, long runSeed, SquareLattice lattice, ClusterStats clusterStats) {
        return new SPPResult(
                run,
                config.L(),
                config.C(),
                0,
                0,
                lattice.initialEdgeCount(),
                0.0,
                clusterStats.largestClusterSize(),
                (double) clusterStats.largestClusterSize() / lattice.vertexCount(),
                clusterStats.secondLargestClusterSize(),
                clusterStats.meanClusterSize(),
                0,
                0,
                runSeed);
    }
}
