package spp;

import java.nio.file.Path;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.List;

/** Immutable, deterministic plan for a sequential parameter sweep. */
public record SPPSweepPlan(
        int[] latticeSizes,
        int[] finiteBudgets,
        boolean includeUnboundedBudget,
        int runs,
        long maxSteps,
        long measurementInterval,
        MeasurementMode measurementMode,
        RunStopMode stopMode,
        double transitionThresholdMultiplier,
        boolean edgeTraceEnabled,
        BoundaryCondition boundaryCondition,
        long baseSeed,
        Path outputDirectory) {

    public enum BudgetMode {
        FINITE,
        UNBOUNDED
    }

    public record Condition(int conditionIndex, int L, int C, BudgetMode budgetMode) {}

    public SPPSweepPlan {
        if (latticeSizes == null || latticeSizes.length == 0) {
            throw new IllegalArgumentException("latticeSizes must not be null or empty");
        }
        if (finiteBudgets == null) {
            throw new IllegalArgumentException("finiteBudgets must not be null");
        }
        if (runs < 1) {
            throw new IllegalArgumentException("runs must be at least 1");
        }
        if (maxSteps < 0) {
            throw new IllegalArgumentException("maxSteps must be non-negative");
        }
        if (measurementInterval < 1) {
            throw new IllegalArgumentException("measurementInterval must be at least 1");
        }
        if (measurementMode == null
                || stopMode == null
                || boundaryCondition == null
                || outputDirectory == null) {
            throw new IllegalArgumentException(
                    "measurementMode, stopMode, boundaryCondition, and outputDirectory must not be null");
        }
        if (!Double.isFinite(transitionThresholdMultiplier)
                || transitionThresholdMultiplier <= 0.0) {
            throw new IllegalArgumentException(
                    "transitionThresholdMultiplier must be finite and positive");
        }
        if (finiteBudgets.length == 0 && !includeUnboundedBudget) {
            throw new IllegalArgumentException("the sweep must contain at least one budget");
        }

        latticeSizes = sortedUniquePositive(latticeSizes, "latticeSizes");
        finiteBudgets = sortedUniquePositive(finiteBudgets, "finiteBudgets");

        // Reuse SPPConfig validation for lattice storage limits and L=1 request processing.
        int validationBudget = finiteBudgets.length == 0 ? 1 : finiteBudgets[0];
        for (int L : latticeSizes) {
            new SPPConfig(
                    L,
                    validationBudget,
                    runs,
                    maxSteps,
                    measurementInterval,
                    measurementMode,
                    stopMode,
                    transitionThresholdMultiplier,
                    edgeTraceEnabled,
                    boundaryCondition,
                    baseSeed,
                    outputDirectory);
        }
    }

    /** Backward-compatible full sweep using the original 1/L transition threshold. */
    public SPPSweepPlan(
            int[] latticeSizes,
            int[] finiteBudgets,
            boolean includeUnboundedBudget,
            int runs,
            long maxSteps,
            long measurementInterval,
            MeasurementMode measurementMode,
            RunStopMode stopMode,
            boolean edgeTraceEnabled,
            BoundaryCondition boundaryCondition,
            long baseSeed,
            Path outputDirectory) {
        this(
                latticeSizes,
                finiteBudgets,
                includeUnboundedBudget,
                runs,
                maxSteps,
                measurementInterval,
                measurementMode,
                stopMode,
                1.0,
                edgeTraceEnabled,
                boundaryCondition,
                baseSeed,
                outputDirectory);
    }

    /** Backward-compatible sweep using the original stop mode and edge tracing. */
    public SPPSweepPlan(
            int[] latticeSizes,
            int[] finiteBudgets,
            boolean includeUnboundedBudget,
            int runs,
            long maxSteps,
            long measurementInterval,
            MeasurementMode measurementMode,
            BoundaryCondition boundaryCondition,
            long baseSeed,
            Path outputDirectory) {
        this(
                latticeSizes,
                finiteBudgets,
                includeUnboundedBudget,
                runs,
                maxSteps,
                measurementInterval,
                measurementMode,
                RunStopMode.MAX_STEPS_OR_ALL_EDGES,
                1.0,
                true,
                boundaryCondition,
                baseSeed,
                outputDirectory);
    }

    @Override
    public int[] latticeSizes() {
        return latticeSizes.clone();
    }

    @Override
    public int[] finiteBudgets() {
        return finiteBudgets.clone();
    }

    /** Returns every condition in stable L/C order, with unbounded last for each L. */
    public List<Condition> conditions() {
        List<Condition> conditions = new ArrayList<>();
        for (int L : latticeSizes) {
            int unboundedBudget = Math.multiplyExact(L, L);
            int unboundedThreshold = unboundedBudget - 1;
            boolean unboundedRequested = includeUnboundedBudget;
            for (int C : finiteBudgets) {
                if (C >= unboundedThreshold) {
                    unboundedRequested = true;
                    continue;
                }
                conditions.add(new Condition(conditions.size(), L, C, BudgetMode.FINITE));
            }
            if (unboundedRequested) {
                conditions.add(
                        new Condition(
                                conditions.size(), L, unboundedBudget, BudgetMode.UNBOUNDED));
            }
        }
        return List.copyOf(conditions);
    }

    public SPPConfig toConfig(Condition condition) {
        if (condition == null) {
            throw new IllegalArgumentException("condition must not be null");
        }
        return new SPPConfig(
                condition.L(),
                condition.C(),
                runs,
                maxSteps,
                measurementInterval,
                measurementMode,
                stopMode,
                transitionThresholdMultiplier,
                edgeTraceEnabled,
                boundaryCondition,
                baseSeed,
                outputDirectory);
    }

    private static int[] sortedUniquePositive(int[] values, String name) {
        int[] copy = values.clone();
        Arrays.sort(copy);
        for (int index = 0; index < copy.length; index++) {
            if (copy[index] < 1) {
                throw new IllegalArgumentException(name + " values must be at least 1");
            }
            if (index > 0 && copy[index] == copy[index - 1]) {
                throw new IllegalArgumentException(name + " must not contain duplicates");
            }
        }
        return copy;
    }
}
