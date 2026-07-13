package spp;

import org.junit.jupiter.api.Test;

import static org.junit.jupiter.api.Assertions.assertArrayEquals;

class BoundaryConditionTest {
    @Test
    void initiallySupportsOnlyOpenBoundary() {
        assertArrayEquals(
                new BoundaryCondition[] {BoundaryCondition.OPEN}, BoundaryCondition.values());
    }
}
