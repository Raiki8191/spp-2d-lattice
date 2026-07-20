package spp;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertNotEquals;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.junit.jupiter.api.Assertions.assertTrue;

import java.io.ByteArrayOutputStream;
import java.io.IOException;
import java.io.PrintStream;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.HashSet;
import java.util.List;
import java.util.Set;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.io.TempDir;

class SPPUnboundedL192Test {
    @TempDir Path temporaryDirectory;

    @Test
    void productionStagesUseDisjointSeedInputsAndExpectedRunCounts() {
        var benchmark = SPPUnboundedL192.benchmarkStage();
        var pilot = SPPUnboundedL192.pilotStage();
        var main = SPPUnboundedL192.mainStage();
        assertEquals(3, benchmark.runs());
        assertEquals(17, pilot.runs());
        assertEquals(30, main.runs());
        Set<Long> seeds = new HashSet<>();
        for (var stage : List.of(benchmark, pilot, main)) {
            for (int run = 0; run < stage.runs(); run++) {
                assertTrue(seeds.add(SeedUtils.runSeed(stage.baseSeed() + run, 0)));
            }
        }
        for (int oldRun = 0; oldRun < 400; oldRun++) {
            assertTrue(seeds.add(SeedUtils.runSeed(42L, oldRun)));
        }
        assertNotEquals(benchmark.outputDirectory(), pilot.outputDirectory());
    }

    @Test
    void skipsValidCompletedShardsAndAggregatesWithoutReexecution() throws IOException {
        var stage = new SPPUnboundedL192.Stage("test", 2, 9000L, 1.0,
                temporaryDirectory.resolve("stage"));
        writeCompletedShard(stage, 0, 5);
        writeCompletedShard(stage, 1, 7);
        ByteArrayOutputStream bytes = new ByteArrayOutputStream();
        Path manifest;
        try (PrintStream output = new PrintStream(bytes, true, StandardCharsets.UTF_8)) {
            manifest = SPPUnboundedL192.run(stage, output);
        }
        assertTrue(bytes.toString(StandardCharsets.UTF_8).contains("resume-skip"));
        assertTrue(Files.isRegularFile(manifest));
        List<String> results = Files.readAllLines(
                stage.outputDirectory().resolve("L=192/C=36864/results.csv"));
        assertEquals(5, results.size());
        assertTrue(results.get(1).startsWith("0,"));
        assertTrue(results.get(3).startsWith("1,"));
        assertEquals(3, Files.readAllLines(stage.outputDirectory().resolve("run_metadata.csv")).size());
    }

    @Test
    void rejectsCorruptCompletedShardInsteadOfSilentlySkippingIt() throws IOException {
        var stage = new SPPUnboundedL192.Stage("corrupt", 1, 9100L, 1.0,
                temporaryDirectory.resolve("corrupt"));
        writeCompletedShard(stage, 0, 5);
        Path result = SPPUnboundedL192.shardDirectory(stage, 0)
                .resolve("L=192/C=36864/results.csv");
        Files.writeString(result, "bad-header\n", StandardCharsets.UTF_8);
        assertThrows(IOException.class, () -> SPPUnboundedL192.run(stage, System.out));
    }

    private void writeCompletedShard(SPPUnboundedL192.Stage stage, int run, long finalStep)
            throws IOException {
        Path shard = SPPUnboundedL192.shardDirectory(stage, run);
        Path condition = shard.resolve("L=192/C=36864");
        Files.createDirectories(condition);
        long seed = SeedUtils.runSeed(stage.baseSeed() + run, 0);
        long m0 = 2L * 192 * 191;
        String first = "0,192,36864,0,0," + m0 + ",0.0,36864,1.0,0,0.0,0,0," + seed;
        String last = "0,192,36864," + finalStep + ",100," + (m0 - 100)
                + ",0.001420,100,0.0027,50,20.0,1," + (finalStep - 1) + "," + seed;
        Files.writeString(condition.resolve("results.csv"),
                CsvWriter.HEADER + "\n" + first + "\n" + last + "\n", StandardCharsets.UTF_8);
        Files.writeString(condition.resolve("run_summary.csv"), RunSummaryWriter.HEADER + "\n0,"
                + seed + "," + finalStep + ",100,0.001420,0.0027,"
                + "TRANSITION_WINDOW_COMPLETE,25\n", StandardCharsets.UTF_8);
        long bytes = Files.size(condition.resolve("results.csv"));
        Files.writeString(shard.resolve("run_metadata.csv"),
                "run,run_seed,started_at_utc,finished_at_utc,elapsed_milliseconds,"
                        + "termination_reason,final_step,final_removed_edges,results_rows,"
                        + "results_bytes,observed_heap_used_bytes,observed_heap_committed_bytes\n"
                        + run + "," + seed + ",2026-01-01T00:00:00Z,2026-01-01T00:00:01Z,25,"
                        + "TRANSITION_WINDOW_COMPLETE," + finalStep + ",100,2," + bytes
                        + ",1000,2000\n", StandardCharsets.UTF_8);
        Files.writeString(shard.resolve(".complete"), "complete\n", StandardCharsets.UTF_8);
    }
}
