package spp;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertNotEquals;

import java.nio.file.Path;
import java.util.List;
import org.junit.jupiter.api.Test;

class SPPScalingV2Test {
    @Test
    void mainPlansUseRequestedRunsStopsAndIndependentOutput() {
        List<SPPSweepPlan> plans = SPPScalingV2.createMainPlans(Path.of("out", "test-v2"));
        assertEquals(6, plans.size());
        for (SPPSweepPlan plan : plans) {
            SPPSweepPlan.Condition condition = plan.conditions().get(0);
            assertEquals(condition.budgetMode() == SPPSweepPlan.BudgetMode.UNBOUNDED ? 400 : 200,
                    plan.runs());
            assertEquals(1.0, plan.transitionThresholdMultiplier());
            assertEquals(MeasurementMode.ACCEPTED_REQUEST, plan.measurementMode());
            assertEquals(RunStopMode.TRANSITION_WINDOW_COMPLETE, plan.stopMode());
            assertFalse(plan.edgeTraceEnabled());
            assertEquals(42L, plan.baseSeed());
            assertEquals(SPPPilot.maxStepsForL(condition.L()), plan.maxSteps());
        }
        assertNotEquals(Path.of("out", "scaling-v1"), plans.get(0).outputDirectory());
    }

    @Test
    void auditPlansUseTwentyRunsAndExtendedThreshold() {
        List<SPPSweepPlan> plans = SPPScalingV2.createStopAuditPlans(Path.of("out", "audit"));
        assertEquals(6, plans.size());
        for (SPPSweepPlan plan : plans) {
            assertEquals(20, plan.runs());
            assertEquals(0.5, plan.transitionThresholdMultiplier());
            assertFalse(plan.edgeTraceEnabled());
        }
    }

    @Test
    void sameRunSeedPolicyIsSharedAcrossBudgets() {
        List<SPPSweepPlan> plans = SPPScalingV2.createMainPlans(Path.of("out", "seed"));
        for (SPPSweepPlan plan : plans) {
            assertEquals(SeedUtils.runSeed(42L, 17), SeedUtils.runSeed(plan.baseSeed(), 17));
        }
    }
}
