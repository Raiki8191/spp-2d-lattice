package spp;

import java.io.IOException;
import java.nio.file.Path;
import java.util.Random;
import java.util.random.RandomGenerator;

/** Runs a configured batch sequentially and writes STEP_INTERVAL measurements to one CSV file. */
public final class SPPExperimentRunner {
    private static final String RESULT_FILE_NAME = "results.csv";

    private final SPPConfig config;
    private final Path outputPath;

    public SPPExperimentRunner(SPPConfig config) {
        if (config == null) {
            throw new IllegalArgumentException("config must not be null");
        }
        this.config = config;
        this.outputPath = resultPath(config);
    }

    /**
     * Executes every run sequentially. The output file is deliberately replaced rather than
     * appended because resume and append modes are outside the initial implementation.
     *
     * @return the CSV file written by this execution
     */
    public Path run() throws IOException {
        ClusterAnalyzer clusterAnalyzer = new ClusterAnalyzer();
        try (CsvWriter csvWriter = CsvWriter.create(outputPath)) {
            for (int run = 0; run < config.runs(); run++) {
                executeRun(run, clusterAnalyzer, csvWriter);
            }
        }
        return outputPath;
    }

    public Path outputPath() {
        return outputPath;
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

    private void executeRun(int run, ClusterAnalyzer clusterAnalyzer, CsvWriter csvWriter)
            throws IOException {
        SquareLattice lattice = new SquareLattice(config.L());
        long runSeed = SeedUtils.runSeed(config.baseSeed(), run);

        // L=1 with maxSteps=0 is a valid structure-only experiment but cannot construct a
        // request processor, which requires two distinct vertices.
        if (lattice.vertexCount() < 2) {
            ClusterStats initialStats = clusterAnalyzer.analyze(lattice);
            csvWriter.write(initialResult(run, runSeed, lattice, initialStats));
            return;
        }

        RandomGenerator pairRandom = new Random(SeedUtils.pairSeed(runSeed));
        RandomGenerator pathRandom = new Random(SeedUtils.pathSeed(runSeed));
        SPPSimulator simulator =
                new SPPSimulator(lattice, config.C(), pairRandom, pathRandom);

        writeMeasurement(run, runSeed, lattice, simulator, clusterAnalyzer, csvWriter);
        long lastMeasuredStep = 0L;

        while (simulator.getStep() < config.maxSteps() && lattice.remainingEdgeCount() > 0) {
            simulator.step();
            if (simulator.getStep() % config.measurementInterval() == 0) {
                writeMeasurement(run, runSeed, lattice, simulator, clusterAnalyzer, csvWriter);
                lastMeasuredStep = simulator.getStep();
            }
        }

        if (simulator.getStep() != lastMeasuredStep) {
            writeMeasurement(run, runSeed, lattice, simulator, clusterAnalyzer, csvWriter);
        }
    }

    private void writeMeasurement(
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
