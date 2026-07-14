package spp;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertTrue;

import java.nio.file.Path;
import java.util.List;
import org.junit.jupiter.api.Test;

class SPPScalingV1Test {
    @Test
    void mainPlanUsesTransitionStopAndNoTrace() {
        SPPSweepPlan plan =
                SPPScalingV1.createPlan(64, new int[] {1, 2}, 200, false, Path.of("out"));

        assertEquals(200, plan.runs());
        assertEquals(33_554_432L, plan.maxSteps());
        assertEquals(MeasurementMode.ACCEPTED_REQUEST, plan.measurementMode());
        assertEquals(RunStopMode.TRANSITION_WINDOW_COMPLETE, plan.stopMode());
        assertFalse(plan.edgeTraceEnabled());
        assertEquals(
                List.of(1, 2, 4096),
                plan.conditions().stream().map(SPPSweepPlan.Condition::C).toList());
    }

    @Test
    void sevenSizesProduceTwentyOneConditions() {
        int conditions = 0;
        for (int L : new int[] {8, 12, 16, 24, 32, 48, 64}) {
            SPPSweepPlan plan =
                    SPPScalingV1.createPlan(L, new int[] {1, 2}, 200, false, Path.of("out"));
            conditions += plan.conditions().size();
            assertTrue(plan.conditions().get(2).budgetMode() == SPPSweepPlan.BudgetMode.UNBOUNDED);
        }
        assertEquals(21, conditions);
    }
}
