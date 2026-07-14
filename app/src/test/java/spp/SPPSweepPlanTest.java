package spp;

import static org.junit.jupiter.api.Assertions.assertArrayEquals;
import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertThrows;

import java.nio.file.Path;
import java.util.List;
import org.junit.jupiter.api.Test;

class SPPSweepPlanTest {
    @Test
    void sortsConditionsAndPlacesUnboundedBudgetLastForEachL() {
        SPPSweepPlan plan = plan(new int[] {6, 4}, new int[] {2, 1}, true);

        List<SPPSweepPlan.Condition> conditions = plan.conditions();
        assertEquals(6, conditions.size());
        assertEquals("4:1:FINITE", description(conditions.get(0)));
        assertEquals("4:2:FINITE", description(conditions.get(1)));
        assertEquals("4:16:UNBOUNDED", description(conditions.get(2)));
        assertEquals("6:1:FINITE", description(conditions.get(3)));
        assertEquals("6:2:FINITE", description(conditions.get(4)));
        assertEquals("6:36:UNBOUNDED", description(conditions.get(5)));
    }

    @Test
    void budgetsAtOrAboveNMinusOneCollapseToOneUnboundedCondition() {
        SPPSweepPlan plan = plan(new int[] {4}, new int[] {2, 15, 16, 20}, true);

        assertEquals(2, plan.conditions().size());
        assertEquals(SPPSweepPlan.BudgetMode.FINITE, plan.conditions().get(0).budgetMode());
        assertEquals(2, plan.conditions().get(0).C());
        assertEquals(SPPSweepPlan.BudgetMode.UNBOUNDED, plan.conditions().get(1).budgetMode());
        assertEquals(16, plan.conditions().get(1).C());
    }

    @Test
    void highFiniteBudgetRequestsUnboundedEvenWhenFlagIsFalse() {
        SPPSweepPlan plan = plan(new int[] {4}, new int[] {2, 15, 16, 20}, false);

        assertEquals(2, plan.conditions().size());
        assertEquals("4:2:FINITE", description(plan.conditions().get(0)));
        assertEquals("4:16:UNBOUNDED", description(plan.conditions().get(1)));
    }

    @Test
    void lowFiniteBudgetsDoNotCreateUnboundedWhenFlagIsFalse() {
        SPPSweepPlan plan = plan(new int[] {4}, new int[] {1, 2}, false);

        assertEquals(2, plan.conditions().size());
        assertEquals("4:1:FINITE", description(plan.conditions().get(0)));
        assertEquals("4:2:FINITE", description(plan.conditions().get(1)));
    }

    @Test
    void smokeSweepStillContainsSixConditions() {
        List<SPPSweepPlan.Condition> conditions =
                ShortestPathPercolation.createSmokeSweepPlan().conditions();

        assertEquals(6, conditions.size());
        assertEquals("4:16:UNBOUNDED", description(conditions.get(2)));
        assertEquals("6:36:UNBOUNDED", description(conditions.get(5)));
    }

    @Test
    void arraysAreDefensivelyCopied() {
        int[] sizes = {6, 4};
        int[] budgets = {2, 1};
        SPPSweepPlan plan = plan(sizes, budgets, true);
        sizes[0] = 99;
        budgets[0] = 99;

        assertArrayEquals(new int[] {4, 6}, plan.latticeSizes());
        assertArrayEquals(new int[] {1, 2}, plan.finiteBudgets());
        int[] returned = plan.latticeSizes();
        returned[0] = 99;
        assertArrayEquals(new int[] {4, 6}, plan.latticeSizes());
    }

    @Test
    void rejectsInvalidArraysAndDuplicateValues() {
        assertThrows(IllegalArgumentException.class, () -> plan(null, new int[] {1}, true));
        assertThrows(IllegalArgumentException.class, () -> plan(new int[0], new int[] {1}, true));
        assertThrows(IllegalArgumentException.class, () -> plan(new int[] {0}, new int[] {1}, true));
        assertThrows(IllegalArgumentException.class, () -> plan(new int[] {4, 4}, new int[] {1}, true));
        assertThrows(IllegalArgumentException.class, () -> plan(new int[] {4}, null, true));
        assertThrows(IllegalArgumentException.class, () -> plan(new int[] {4}, new int[] {0}, true));
        assertThrows(IllegalArgumentException.class, () -> plan(new int[] {4}, new int[] {1, 1}, true));
        assertThrows(IllegalArgumentException.class, () -> plan(new int[] {4}, new int[0], false));
    }

    @Test
    void rejectsInvalidScalarAndNullValues() {
        assertThrows(IllegalArgumentException.class, () -> fullPlan(0, 1, MeasurementMode.STEP_INTERVAL, BoundaryCondition.OPEN, Path.of("out")));
        assertThrows(IllegalArgumentException.class, () -> fullPlan(1, -1, MeasurementMode.STEP_INTERVAL, BoundaryCondition.OPEN, Path.of("out")));
        assertThrows(
                IllegalArgumentException.class,
                () ->
                        new SPPSweepPlan(
                                new int[] {4},
                                new int[] {1},
                                false,
                                1,
                                0,
                                0,
                                MeasurementMode.STEP_INTERVAL,
                                BoundaryCondition.OPEN,
                                42,
                                Path.of("out")));
        assertThrows(IllegalArgumentException.class, () -> fullPlan(1, 1, null, BoundaryCondition.OPEN, Path.of("out")));
        assertThrows(IllegalArgumentException.class, () -> fullPlan(1, 1, MeasurementMode.STEP_INTERVAL, null, Path.of("out")));
        assertThrows(IllegalArgumentException.class, () -> fullPlan(1, 1, MeasurementMode.STEP_INTERVAL, BoundaryCondition.OPEN, null));
    }

    private static SPPSweepPlan plan(int[] sizes, int[] budgets, boolean unbounded) {
        return new SPPSweepPlan(
                sizes,
                budgets,
                unbounded,
                1,
                0,
                1,
                MeasurementMode.STEP_INTERVAL,
                BoundaryCondition.OPEN,
                42,
                Path.of("out"));
    }

    private static SPPSweepPlan fullPlan(
            int runs,
            long maxSteps,
            MeasurementMode mode,
            BoundaryCondition boundary,
            Path output) {
        return new SPPSweepPlan(
                new int[] {4}, new int[] {1}, false, runs, maxSteps, 1, mode, boundary, 42, output);
    }

    private static String description(SPPSweepPlan.Condition condition) {
        return condition.L() + ":" + condition.C() + ":" + condition.budgetMode();
    }
}
