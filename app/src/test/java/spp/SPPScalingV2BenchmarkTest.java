package spp;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;

import java.nio.file.Path;
import org.junit.jupiter.api.Test;

class SPPScalingV2BenchmarkTest {
    @Test
    void createsRequestedExtendedTransitionPlan() {
        SPPSweepPlan plan = SPPScalingV2Benchmark.createPlan(128, 5, Path.of("out"));

        assertEquals(5, plan.runs());
        assertEquals(2L * 128 * 128 * 128 * 128, plan.maxSteps());
        assertEquals(MeasurementMode.ACCEPTED_REQUEST, plan.measurementMode());
        assertEquals(RunStopMode.TRANSITION_WINDOW_COMPLETE, plan.stopMode());
        assertEquals(0.5, plan.transitionThresholdMultiplier());
        assertFalse(plan.edgeTraceEnabled());
        assertEquals(3, plan.conditions().size());
        assertEquals(16_384, plan.conditions().get(2).C());
        assertEquals(SPPSweepPlan.BudgetMode.UNBOUNDED, plan.conditions().get(2).budgetMode());
    }
}
