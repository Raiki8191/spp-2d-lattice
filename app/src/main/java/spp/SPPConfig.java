package spp;

import java.nio.file.Path;

/** Immutable configuration for an SPP simulation batch. */
public record SPPConfig(
        int L,
        int C,
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

    private static final int MAX_DEGREE = 4;

    public SPPConfig {
        if (L < 1) {
            throw new IllegalArgumentException("L must be at least 1");
        }
        if (C < 1) {
            throw new IllegalArgumentException("C must be at least 1");
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
        if (measurementMode == null) {
            throw new IllegalArgumentException("measurementMode must not be null");
        }
        if (stopMode == null) {
            throw new IllegalArgumentException("stopMode must not be null");
        }
        if (!Double.isFinite(transitionThresholdMultiplier)
                || transitionThresholdMultiplier <= 0.0) {
            throw new IllegalArgumentException(
                    "transitionThresholdMultiplier must be finite and positive");
        }
        if (stopMode == RunStopMode.TRANSITION_WINDOW_COMPLETE
                && measurementMode != MeasurementMode.ACCEPTED_REQUEST) {
            throw new IllegalArgumentException(
                    "TRANSITION_WINDOW_COMPLETE requires ACCEPTED_REQUEST measurements");
        }
        if (boundaryCondition == null) {
            throw new IllegalArgumentException("boundaryCondition must not be null");
        }
        if (boundaryCondition != BoundaryCondition.OPEN) {
            throw new IllegalArgumentException("unsupported boundary condition: " + boundaryCondition);
        }
        if (outputDirectory == null) {
            throw new IllegalArgumentException("outputDirectory must not be null");
        }

        long vertexCount = (long) L * L;
        long initialEdgeCount = 2L * L * (L - 1L);
        if (vertexCount > Integer.MAX_VALUE) {
            throw new IllegalArgumentException("L is too large: vertex count exceeds int range");
        }
        if (initialEdgeCount > Integer.MAX_VALUE) {
            throw new IllegalArgumentException("L is too large: edge count exceeds int range");
        }
        long adjacencySlotCount = vertexCount * MAX_DEGREE;
        if (adjacencySlotCount > Integer.MAX_VALUE) {
            throw new IllegalArgumentException("L is too large: adjacency storage exceeds int range");
        }
        if (maxSteps > 0 && vertexCount < 2) {
            throw new IllegalArgumentException("maxSteps > 0 requires at least two vertices");
        }
    }

    /** Backward-compatible full configuration using the original 1/L transition threshold. */
    public SPPConfig(
            int L,
            int C,
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
                L,
                C,
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

    /** Backward-compatible configuration with the original stop mode and edge tracing. */
    public SPPConfig(
            int L,
            int C,
            int runs,
            long maxSteps,
            long measurementInterval,
            MeasurementMode measurementMode,
            BoundaryCondition boundaryCondition,
            long baseSeed,
            Path outputDirectory) {
        this(
                L,
                C,
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

    /** Backward-compatible configuration using STEP_INTERVAL measurements. */
    public SPPConfig(
            int L,
            int C,
            int runs,
            long maxSteps,
            long measurementInterval,
            BoundaryCondition boundaryCondition,
            long baseSeed,
            Path outputDirectory) {
        this(
                L,
                C,
                runs,
                maxSteps,
                measurementInterval,
                MeasurementMode.STEP_INTERVAL,
                RunStopMode.MAX_STEPS_OR_ALL_EDGES,
                1.0,
                true,
                boundaryCondition,
                baseSeed,
                outputDirectory);
    }
}
