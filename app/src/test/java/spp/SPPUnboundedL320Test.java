package spp;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertTrue;

import java.util.HashSet;
import java.util.List;
import java.util.Set;
import org.junit.jupiter.api.Test;

class SPPUnboundedL320Test {
    @Test
    void stagesUseL320UnboundedBudgetAndDisjointSeeds() {
        var benchmark = SPPUnboundedL320.benchmarkStage();
        var pilot = SPPUnboundedL320.pilotStage();
        assertEquals(320, benchmark.latticeSize());
        assertEquals(102_400, benchmark.budget());
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
                SPPUnboundedL192.mainStage(), SPPUnboundedL256.benchmarkStage(),
                SPPUnboundedL256.pilotStage())) {
            for (int run = 0; run < oldStage.runs(); run++) {
                assertTrue(seeds.add(SeedUtils.runSeed(oldStage.baseSeed() + run, 0)));
            }
        }
    }

    @Test
    void earlierStageConfigurationsRemainUnchanged() {
        assertEquals(192, SPPUnboundedL192.benchmarkStage().latticeSize());
        assertEquals(36_864, SPPUnboundedL192.benchmarkStage().budget());
        assertEquals(256, SPPUnboundedL256.benchmarkStage().latticeSize());
        assertEquals(65_536, SPPUnboundedL256.benchmarkStage().budget());
    }
}
