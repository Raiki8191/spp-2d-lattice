package spp;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertTrue;

import java.util.HashSet;
import java.util.List;
import java.util.Set;
import org.junit.jupiter.api.Test;

class SPPUnboundedL384Test {
    @Test
    void stagesUseL384UnboundedBudgetAndDisjointProductionSeeds() {
        var benchmark = SPPUnboundedL384.benchmarkStage();
        var pilot = SPPUnboundedL384.pilotStage();
        assertEquals(384, benchmark.latticeSize());
        assertEquals(147_456, benchmark.budget());
        assertEquals(3, benchmark.runs());
        assertEquals(17, pilot.runs());
        assertEquals(benchmark.baseSeed(), SPPUnboundedL384.auditStage().baseSeed());
        Set<Long> seeds = new HashSet<>();
        for (var stage : List.of(benchmark, pilot)) {
            for (int run = 0; run < stage.runs(); run++) {
                assertTrue(seeds.add(SeedUtils.runSeed(stage.baseSeed() + run, 0)));
            }
        }
        for (var oldStage : List.of(
                SPPUnboundedL192.benchmarkStage(), SPPUnboundedL192.pilotStage(),
                SPPUnboundedL192.mainStage(), SPPUnboundedL256.benchmarkStage(),
                SPPUnboundedL256.pilotStage(), SPPUnboundedL320.benchmarkStage(),
                SPPUnboundedL320.pilotStage())) {
            for (int run = 0; run < oldStage.runs(); run++) {
                assertTrue(seeds.add(SeedUtils.runSeed(oldStage.baseSeed() + run, 0)));
            }
        }
    }

    @Test
    void earlierStageConfigurationsRemainUnchanged() {
        assertEquals(192, SPPUnboundedL192.benchmarkStage().latticeSize());
        assertEquals(256, SPPUnboundedL256.benchmarkStage().latticeSize());
        assertEquals(320, SPPUnboundedL320.benchmarkStage().latticeSize());
    }
}
