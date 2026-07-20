package spp;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.junit.jupiter.api.Assertions.assertTrue;

import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.HashSet;
import java.util.List;
import java.util.Set;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.io.TempDir;

class SPPUnboundedL256Test {
    @TempDir Path temporaryDirectory;

    @Test
    void stagesUseL256UnboundedBudgetAndDisjointSeeds() {
        var benchmark = SPPUnboundedL256.benchmarkStage();
        var pilot = SPPUnboundedL256.pilotStage();
        assertEquals(256, benchmark.latticeSize());
        assertEquals(65_536, benchmark.budget());
        assertEquals(3, benchmark.runs());
        assertEquals(17, pilot.runs());
        Set<Long> seeds = new HashSet<>();
        for (var stage : List.of(benchmark, pilot)) {
            for (int run = 0; run < stage.runs(); run++) {
                assertTrue(seeds.add(SeedUtils.runSeed(stage.baseSeed() + run, 0)));
            }
        }
        for (var oldStage : List.of(
                SPPUnboundedL192.benchmarkStage(), SPPUnboundedL192.pilotStage(),
                SPPUnboundedL192.mainStage())) {
            for (int run = 0; run < oldStage.runs(); run++) {
                assertTrue(seeds.add(SeedUtils.runSeed(oldStage.baseSeed() + run, 0)));
            }
        }
    }

    @Test
    void l192ConfigurationsRemainUnchangedAfterSharingEngine() {
        for (var stage : List.of(
                SPPUnboundedL192.benchmarkStage(), SPPUnboundedL192.pilotStage(),
                SPPUnboundedL192.mainStage(), SPPUnboundedL192.auditStage())) {
            assertEquals(192, stage.latticeSize());
            assertEquals(36_864, stage.budget());
        }
    }

    @Test
    void missingCompletedShardIsRejected() throws IOException {
        var stage = new SPPUnboundedL192.Stage(
                "missing", 256, 1, 2_569_000L, 1.0, temporaryDirectory);
        Path shard = SPPUnboundedL192.shardDirectory(stage, 0);
        Files.createDirectories(shard);
        Files.writeString(shard.resolve(".complete"), "complete\n", StandardCharsets.UTF_8);

        IOException error = assertThrows(
                IOException.class, () -> SPPUnboundedL192.run(stage, System.out));
        assertTrue(error.getMessage().contains("incomplete shard"));
        assertFalse(Files.exists(temporaryDirectory.resolve("manifest.csv")));
    }
}
