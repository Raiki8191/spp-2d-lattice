package spp;

import java.nio.file.Path;

import org.junit.jupiter.api.Test;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertThrows;

class SPPConfigTest {
    private static final Path OUTPUT_DIRECTORY = Path.of("results");

    @Test
    void createsValidConfiguration() {
        SPPConfig config = config(16, 8, 10, 1_000, 25, BoundaryCondition.OPEN, OUTPUT_DIRECTORY);

        assertEquals(16, config.L());
        assertEquals(8, config.C());
        assertEquals(10, config.runs());
        assertEquals(1_000, config.maxSteps());
        assertEquals(25, config.measurementInterval());
        assertEquals(MeasurementMode.STEP_INTERVAL, config.measurementMode());
        assertEquals(BoundaryCondition.OPEN, config.boundaryCondition());
        assertEquals(12345L, config.baseSeed());
        assertEquals(OUTPUT_DIRECTORY, config.outputDirectory());
    }

    @Test
    void rejectsInvalidSideLength() {
        assertThrows(IllegalArgumentException.class,
                () -> config(0, 1, 1, 0, 1, BoundaryCondition.OPEN, OUTPUT_DIRECTORY));
    }

    @Test
    void rejectsInvalidBudget() {
        assertThrows(IllegalArgumentException.class,
                () -> config(2, 0, 1, 0, 1, BoundaryCondition.OPEN, OUTPUT_DIRECTORY));
    }

    @Test
    void rejectsInvalidRunCount() {
        assertThrows(IllegalArgumentException.class,
                () -> config(2, 1, 0, 0, 1, BoundaryCondition.OPEN, OUTPUT_DIRECTORY));
    }

    @Test
    void rejectsNegativeMaxSteps() {
        assertThrows(IllegalArgumentException.class,
                () -> config(2, 1, 1, -1, 1, BoundaryCondition.OPEN, OUTPUT_DIRECTORY));
    }

    @Test
    void rejectsInvalidMeasurementInterval() {
        assertThrows(IllegalArgumentException.class,
                () -> config(2, 1, 1, 0, 0, BoundaryCondition.OPEN, OUTPUT_DIRECTORY));
    }

    @Test
    void createsAcceptedRequestConfiguration() {
        SPPConfig config =
                new SPPConfig(
                        16,
                        8,
                        10,
                        1_000,
                        25,
                        MeasurementMode.ACCEPTED_REQUEST,
                        BoundaryCondition.OPEN,
                        12345L,
                        OUTPUT_DIRECTORY);

        assertEquals(MeasurementMode.ACCEPTED_REQUEST, config.measurementMode());
        assertEquals(25, config.measurementInterval());
    }

    @Test
    void rejectsNullMeasurementMode() {
        assertThrows(
                IllegalArgumentException.class,
                () ->
                        new SPPConfig(
                                2,
                                1,
                                1,
                                0,
                                1,
                                null,
                                BoundaryCondition.OPEN,
                                12345L,
                                OUTPUT_DIRECTORY));
    }

    @Test
    void rejectsNullBoundaryCondition() {
        assertThrows(IllegalArgumentException.class,
                () -> config(2, 1, 1, 0, 1, null, OUTPUT_DIRECTORY));
    }

    @Test
    void rejectsNullOutputDirectory() {
        assertThrows(IllegalArgumentException.class,
                () -> config(2, 1, 1, 0, 1, BoundaryCondition.OPEN, null));
    }

    @Test
    void allowsSingleVertexWhenNoRequestsAreProcessed() {
        SPPConfig config = config(1, 1, 1, 0, 1, BoundaryCondition.OPEN, OUTPUT_DIRECTORY);

        assertEquals(1, config.L());
    }

    @Test
    void rejectsSingleVertexWhenRequestsAreProcessed() {
        assertThrows(IllegalArgumentException.class,
                () -> config(1, 1, 1, 1, 1, BoundaryCondition.OPEN, OUTPUT_DIRECTORY));
    }

    @Test
    void rejectsSideLengthWhoseAdjacencyStorageExceedsIntRange() {
        assertThrows(IllegalArgumentException.class,
                () -> config(24_000, 1, 1, 0, 1, BoundaryCondition.OPEN, OUTPUT_DIRECTORY));
    }

    @Test
    void rejectsSideLengthWhoseEdgeCountExceedsIntRange() {
        assertThrows(IllegalArgumentException.class,
                () -> config(40_000, 1, 1, 0, 1, BoundaryCondition.OPEN, OUTPUT_DIRECTORY));
    }

    @Test
    void rejectsSideLengthWhoseVertexCountExceedsIntRange() {
        assertThrows(IllegalArgumentException.class,
                () -> config(50_000, 1, 1, 0, 1, BoundaryCondition.OPEN, OUTPUT_DIRECTORY));
    }

    private static SPPConfig config(
            int L,
            int C,
            int runs,
            long maxSteps,
            long measurementInterval,
            BoundaryCondition boundaryCondition,
            Path outputDirectory) {
        return new SPPConfig(
                L,
                C,
                runs,
                maxSteps,
                measurementInterval,
                boundaryCondition,
                12345L,
                outputDirectory);
    }
}
