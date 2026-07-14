package spp;

import static org.junit.jupiter.api.Assertions.assertEquals;

import java.nio.file.Path;
import java.util.List;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.io.TempDir;

class SPPScalingBenchmarkTest {
    @TempDir Path temporaryDirectory;

    @Test
    void createsOnlyTheRequestedSmallBenchmarkConditions() {
        SPPSweepPlan plan24 = SPPScalingBenchmark.createPlan(24, temporaryDirectory);
        SPPSweepPlan plan32 = SPPScalingBenchmark.createPlan(32, temporaryDirectory);

        assertPlan(plan24, 24, 663_552L, List.of(1, 2, 576));
        assertPlan(plan32, 32, 2_097_152L, List.of(1, 2, 1024));
    }

    private static void assertPlan(
            SPPSweepPlan plan, int L, long maxSteps, List<Integer> budgets) {
        assertEquals(3, plan.runs());
        assertEquals(maxSteps, plan.maxSteps());
        assertEquals(MeasurementMode.ACCEPTED_REQUEST, plan.measurementMode());
        assertEquals(42L, plan.baseSeed());
        assertEquals(
                budgets, plan.conditions().stream().map(SPPSweepPlan.Condition::C).toList());
        assertEquals(1, plan.latticeSizes().length);
        assertEquals(L, plan.latticeSizes()[0]);
    }
}
