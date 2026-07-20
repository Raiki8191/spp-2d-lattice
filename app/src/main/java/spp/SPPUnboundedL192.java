package spp;

import java.io.BufferedWriter;
import java.io.IOException;
import java.io.PrintStream;
import java.lang.management.ManagementFactory;
import java.lang.management.MemoryMXBean;
import java.lang.management.MemoryUsage;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.StandardOpenOption;
import java.time.Instant;
import java.util.ArrayList;
import java.util.Collections;
import java.util.List;

/** Resumable, staged UNBOUNDED L=192 experiment used by the v4 analysis. */
public final class SPPUnboundedL192 {
    public static final int L = 192;
    public static final int C = L * L;
    public static final int BENCHMARK_RUNS = 3;
    public static final int PILOT_RUNS = 17;
    public static final int MAIN_RUNS = 30;
    public static final long BENCHMARK_BASE_SEED = 1_920_000L;
    public static final long PILOT_BASE_SEED = BENCHMARK_BASE_SEED + BENCHMARK_RUNS;
    public static final long MAIN_BASE_SEED = PILOT_BASE_SEED + PILOT_RUNS;
    public static final Path ROOT = Path.of("out", "unbounded-l192");

    private static final String METADATA_HEADER =
            "run,run_seed,started_at_utc,finished_at_utc,elapsed_milliseconds,"
                    + "termination_reason,final_step,final_removed_edges,results_rows,"
                    + "results_bytes,observed_heap_used_bytes,observed_heap_committed_bytes";

    private SPPUnboundedL192() {}

    public record Stage(
            String name,
            int runs,
            long baseSeed,
            double transitionThresholdMultiplier,
            Path outputDirectory) {
        public Stage {
            if (name == null || name.isBlank() || runs < 1 || outputDirectory == null) {
                throw new IllegalArgumentException("stage name, positive runs and output are required");
            }
            if (!Double.isFinite(transitionThresholdMultiplier)
                    || transitionThresholdMultiplier <= 0.0) {
                throw new IllegalArgumentException("transition threshold must be positive");
            }
        }
    }

    public static Stage benchmarkStage() {
        return new Stage("unbounded-l192-benchmark", BENCHMARK_RUNS,
                BENCHMARK_BASE_SEED, 1.0, ROOT.resolve("benchmark"));
    }

    public static Stage pilotStage() {
        return new Stage("unbounded-l192-pilot", PILOT_RUNS,
                PILOT_BASE_SEED, 1.0, ROOT.resolve("pilot"));
    }

    public static Stage mainStage() {
        return new Stage("unbounded-l192-main", MAIN_RUNS,
                MAIN_BASE_SEED, 1.0, ROOT.resolve("main"));
    }

    /** A separate, shorter-seed audit continued to P <= 0.5/L. */
    public static Stage auditStage() {
        return new Stage("unbounded-l192-stop-audit", BENCHMARK_RUNS,
                BENCHMARK_BASE_SEED, 0.5, ROOT.resolve("stop-audit"));
    }

    public static Path run(Stage stage, PrintStream output) throws IOException {
        if (stage == null || output == null) {
            throw new IllegalArgumentException("stage and output must not be null");
        }
        Files.createDirectories(stage.outputDirectory());
        List<Long> elapsed = new ArrayList<>();
        long stageStarted = System.nanoTime();
        for (int run = 0; run < stage.runs(); run++) {
            Path shard = shardDirectory(stage, run);
            Path marker = shard.resolve(".complete");
            if (Files.exists(marker)) {
                RunRecord record = validateShard(stage, run);
                elapsed.add(record.elapsedMilliseconds());
                output.println("resume-skip stage=" + stage.name() + " run=" + run);
            } else {
                RunRecord record = executeShard(stage, run);
                validateShard(stage, run);
                Files.writeString(marker, "complete\n", StandardCharsets.UTF_8,
                        StandardOpenOption.CREATE, StandardOpenOption.TRUNCATE_EXISTING);
                elapsed.add(record.elapsedMilliseconds());
            }
            reportProgress(stage, run + 1, elapsed, stageStarted, output);
        }
        aggregate(stage);
        Path manifest = writeManifest(stage);
        output.println("stage-complete name=" + stage.name() + " manifest="
                + manifest.toAbsolutePath());
        return manifest;
    }

    static Path shardDirectory(Stage stage, int run) {
        return stage.outputDirectory().resolve("shards").resolve(String.format("run=%04d", run));
    }

    private static RunRecord executeShard(Stage stage, int run) throws IOException {
        Path shard = shardDirectory(stage, run);
        Files.createDirectories(shard);
        long seedInput = Math.addExact(stage.baseSeed(), run);
        Instant started = Instant.now();
        long startedNanos = System.nanoTime();
        SPPConfig config = new SPPConfig(
                L, C, 1, SPPPilot.maxStepsForL(L), 1,
                MeasurementMode.ACCEPTED_REQUEST,
                RunStopMode.TRANSITION_WINDOW_COMPLETE,
                stage.transitionThresholdMultiplier(), false,
                BoundaryCondition.OPEN, seedInput, shard);
        SPPExperimentRunner runner = new SPPExperimentRunner(config);
        runner.run();
        long elapsed = (System.nanoTime() - startedNanos) / 1_000_000L;
        Instant finished = Instant.now();
        Path results = runner.outputPath();
        Path summary = runner.runSummaryPath();
        String[] finalFields = readSingleSummary(summary);
        MemoryUsage heap = memoryUsage();
        long rows = countDataRows(results);
        RunRecord record = new RunRecord(
                run, Long.parseLong(finalFields[1]), started.toString(), finished.toString(), elapsed,
                finalFields[6], Long.parseLong(finalFields[2]), Long.parseLong(finalFields[3]),
                rows, Files.size(results), heap.getUsed(), heap.getCommitted());
        writeMetadata(shard.resolve("run_metadata.csv"), record);
        return record;
    }

    static RunRecord validateShard(Stage stage, int run) throws IOException {
        Path shard = shardDirectory(stage, run);
        Path condition = shard.resolve("L=" + L).resolve("C=" + C);
        Path results = condition.resolve("results.csv");
        Path summary = condition.resolve("run_summary.csv");
        Path metadata = shard.resolve("run_metadata.csv");
        if (!Files.isRegularFile(results) || !Files.isRegularFile(summary)
                || !Files.isRegularFile(metadata)) {
            throw new IOException("incomplete shard for stage=" + stage.name() + " run=" + run);
        }
        List<String> lines = Files.readAllLines(results, StandardCharsets.UTF_8);
        if (lines.size() < 2 || !CsvWriter.HEADER.equals(lines.get(0))) {
            throw new IOException("invalid results header or empty shard: " + results);
        }
        long previousStep = -1;
        long previousRemoved = -1;
        long previousAccepted = -1;
        long finalRemoved = -1;
        long expectedSeed = SeedUtils.runSeed(Math.addExact(stage.baseSeed(), run), 0);
        for (int index = 1; index < lines.size(); index++) {
            String[] fields = lines.get(index).split(",", -1);
            if (fields.length != 14) {
                throw new IOException("results row does not have 14 columns: " + results);
            }
            long step = Long.parseLong(fields[3]);
            long removed = Long.parseLong(fields[4]);
            long remaining = Long.parseLong(fields[5]);
            long accepted = Long.parseLong(fields[11]);
            long rejected = Long.parseLong(fields[12]);
            if (!"0".equals(fields[0]) || Integer.parseInt(fields[1]) != L
                    || Integer.parseInt(fields[2]) != C || Long.parseLong(fields[13]) != expectedSeed
                    || step <= previousStep || removed < previousRemoved || accepted < previousAccepted
                    || accepted + rejected != step || removed + remaining != 2L * L * (L - 1L)) {
                throw new IOException("results invariant violation at row=" + index + ": " + results);
            }
            previousStep = step;
            previousRemoved = removed;
            previousAccepted = accepted;
            finalRemoved = removed;
        }
        String[] summaryFields = readSingleSummary(summary);
        if (!"TRANSITION_WINDOW_COMPLETE".equals(summaryFields[6])
                || Long.parseLong(summaryFields[1]) != expectedSeed
                || Long.parseLong(summaryFields[2]) != previousStep
                || Long.parseLong(summaryFields[3]) != finalRemoved) {
            throw new IOException("run summary does not match terminal results: " + summary);
        }
        RunRecord record = readMetadata(metadata);
        if (record.run() != run || record.runSeed() != expectedSeed
                || record.resultsRows() != lines.size() - 1L
                || !record.terminationReason().equals(summaryFields[6])) {
            throw new IOException("run metadata mismatch: " + metadata);
        }
        return record;
    }

    private static void aggregate(Stage stage) throws IOException {
        Path condition = stage.outputDirectory().resolve("L=" + L).resolve("C=" + C);
        Files.createDirectories(condition);
        try (BufferedWriter results = writer(condition.resolve("results.csv"));
                BufferedWriter summaries = writer(condition.resolve("run_summary.csv"));
                BufferedWriter metadata = writer(stage.outputDirectory().resolve("run_metadata.csv"))) {
            results.write(CsvWriter.HEADER); results.newLine();
            summaries.write(RunSummaryWriter.HEADER); summaries.newLine();
            metadata.write(METADATA_HEADER); metadata.newLine();
            for (int run = 0; run < stage.runs(); run++) {
                validateShard(stage, run);
                Path shard = shardDirectory(stage, run);
                Path shardCondition = shard.resolve("L=" + L).resolve("C=" + C);
                copyDataRows(shardCondition.resolve("results.csv"), results, run);
                copyDataRows(shardCondition.resolve("run_summary.csv"), summaries, run);
                copyDataRows(shard.resolve("run_metadata.csv"), metadata, run);
            }
        }
    }

    private static Path writeManifest(Stage stage) throws IOException {
        Path manifest = stage.outputDirectory().resolve("manifest.csv");
        try (BufferedWriter writer = writer(manifest)) {
            writer.write(SweepManifestWriter.HEADER_WITHOUT_EDGE_TRACE
                    + ",stage,run_metadata_path");
            writer.newLine();
            writer.write("0," + L + "," + C + ",UNBOUNDED," + stage.runs() + ","
                    + SPPPilot.maxStepsForL(L) + ",ACCEPTED_REQUEST,1," + stage.baseSeed()
                    + ",L=" + L + "/C=" + C + "/results.csv,TRANSITION_WINDOW_COMPLETE,"
                    + stage.transitionThresholdMultiplier() + "," + stage.name()
                    + ",run_metadata.csv");
            writer.newLine();
        }
        return manifest;
    }

    private static void reportProgress(
            Stage stage, int completed, List<Long> elapsed, long stageStarted, PrintStream output)
            throws IOException {
        List<Long> ordered = new ArrayList<>(elapsed);
        Collections.sort(ordered);
        long median = ordered.get((ordered.size() - 1) / 2);
        int remaining = stage.runs() - completed;
        long totalElapsed = (System.nanoTime() - stageStarted) / 1_000_000L;
        long bytes = directoryBytes(stage.outputDirectory());
        output.println("progress stage=" + stage.name() + " completed=" + completed
                + " remaining=" + remaining + " elapsed_ms=" + totalElapsed
                + " current_run_median_ms=" + median + " estimated_remaining_ms="
                + median * remaining + " output_bytes=" + bytes
                + " estimate_note=median-based-not-guaranteed");
    }

    private static void copyDataRows(Path source, BufferedWriter target, int run) throws IOException {
        List<String> lines = Files.readAllLines(source, StandardCharsets.UTF_8);
        for (int index = 1; index < lines.size(); index++) {
            String line = lines.get(index);
            int comma = line.indexOf(',');
            target.write(run + line.substring(comma));
            target.newLine();
        }
    }

    private static long directoryBytes(Path root) throws IOException {
        try (var stream = Files.walk(root)) {
            return stream.filter(Files::isRegularFile).mapToLong(path -> {
                try { return Files.size(path); } catch (IOException error) { return 0L; }
            }).sum();
        }
    }

    private static BufferedWriter writer(Path path) throws IOException {
        Path parent = path.toAbsolutePath().getParent();
        if (parent != null) Files.createDirectories(parent);
        return Files.newBufferedWriter(path, StandardCharsets.UTF_8,
                StandardOpenOption.CREATE, StandardOpenOption.TRUNCATE_EXISTING,
                StandardOpenOption.WRITE);
    }

    private static long countDataRows(Path path) throws IOException {
        try (var lines = Files.lines(path, StandardCharsets.UTF_8)) {
            return Math.max(0L, lines.count() - 1L);
        }
    }

    private static String[] readSingleSummary(Path path) throws IOException {
        List<String> lines = Files.readAllLines(path, StandardCharsets.UTF_8);
        if (lines.size() != 2 || !RunSummaryWriter.HEADER.equals(lines.get(0))) {
            throw new IOException("expected exactly one run summary: " + path);
        }
        String[] fields = lines.get(1).split(",", -1);
        if (fields.length != 8) throw new IOException("invalid run summary: " + path);
        return fields;
    }

    private static MemoryUsage memoryUsage() {
        MemoryMXBean bean = ManagementFactory.getMemoryMXBean();
        return bean.getHeapMemoryUsage();
    }

    private static void writeMetadata(Path path, RunRecord record) throws IOException {
        try (BufferedWriter writer = writer(path)) {
            writer.write(METADATA_HEADER); writer.newLine();
            writer.write(record.toCsv()); writer.newLine();
        }
    }

    private static RunRecord readMetadata(Path path) throws IOException {
        List<String> lines = Files.readAllLines(path, StandardCharsets.UTF_8);
        if (lines.size() != 2 || !METADATA_HEADER.equals(lines.get(0))) {
            throw new IOException("invalid metadata: " + path);
        }
        return RunRecord.parse(lines.get(1));
    }

    record RunRecord(
            int run, long runSeed, String startedAtUtc, String finishedAtUtc,
            long elapsedMilliseconds, String terminationReason, long finalStep,
            long finalRemovedEdges, long resultsRows, long resultsBytes,
            long observedHeapUsedBytes, long observedHeapCommittedBytes) {
        String toCsv() {
            return run + "," + runSeed + "," + startedAtUtc + "," + finishedAtUtc + ","
                    + elapsedMilliseconds + "," + terminationReason + "," + finalStep + ","
                    + finalRemovedEdges + "," + resultsRows + "," + resultsBytes + ","
                    + observedHeapUsedBytes + "," + observedHeapCommittedBytes;
        }
        static RunRecord parse(String csv) {
            String[] f = csv.split(",", -1);
            if (f.length != 12) throw new IllegalArgumentException("invalid run metadata row");
            return new RunRecord(Integer.parseInt(f[0]), Long.parseLong(f[1]), f[2], f[3],
                    Long.parseLong(f[4]), f[5], Long.parseLong(f[6]), Long.parseLong(f[7]),
                    Long.parseLong(f[8]), Long.parseLong(f[9]), Long.parseLong(f[10]),
                    Long.parseLong(f[11]));
        }
    }
}
