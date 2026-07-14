package spp;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertThrows;

import java.nio.file.Path;
import org.junit.jupiter.api.Test;

class SPPPilotTest {
    @Test
    void computesSpecifiedMaxStepsFromL() {
        assertEquals(8_192L, SPPPilot.maxStepsForL(8));
        assertEquals(41_472L, SPPPilot.maxStepsForL(12));
        assertEquals(131_072L, SPPPilot.maxStepsForL(16));
        assertThrows(IllegalArgumentException.class, () -> SPPPilot.maxStepsForL(0));
    }

    @Test
    void createsAcceptedRequestPlanForOneL() {
        SPPSweepPlan plan = SPPPilot.createPlan(12, Path.of("pilot"));

        assertEquals(3, plan.conditions().size());
        assertEquals(10, plan.runs());
        assertEquals(41_472L, plan.maxSteps());
        assertEquals(1, plan.measurementInterval());
        assertEquals(MeasurementMode.ACCEPTED_REQUEST, plan.measurementMode());
        assertEquals(144, plan.conditions().get(2).C());
        assertEquals(SPPSweepPlan.BudgetMode.UNBOUNDED, plan.conditions().get(2).budgetMode());
    }
}
