package spp;

import org.junit.jupiter.api.Test;

import static org.junit.jupiter.api.Assertions.assertDoesNotThrow;
import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertThrows;

class SPPStepResultTest {
    @Test
    void acceptsValidAcceptedAndRejectedResults() {
        SPPStepResult accepted = new SPPStepResult(1, 0, 1, true, 1, 1, 1, 0);
        SPPStepResult rejected = new SPPStepResult(2, 1, 0, false, -1, 0, 1, 1);

        assertEquals(1, accepted.pathLength());
        assertEquals(-1, rejected.pathLength());
    }

    @Test
    void rejectsInvalidCommonFieldsAndCounters() {
        assertThrows(IllegalArgumentException.class,
                () -> new SPPStepResult(0, 0, 1, true, 1, 1, 1, 0));
        assertThrows(IllegalArgumentException.class,
                () -> new SPPStepResult(1, -1, 1, true, 1, 1, 1, 0));
        assertThrows(IllegalArgumentException.class,
                () -> new SPPStepResult(1, 0, -1, true, 1, 1, 1, 0));
        assertThrows(IllegalArgumentException.class,
                () -> new SPPStepResult(1, 0, 0, true, 1, 1, 1, 0));
        assertThrows(IllegalArgumentException.class,
                () -> new SPPStepResult(2, 0, 1, true, 1, 1, 1, 0));
        assertThrows(IllegalArgumentException.class,
                () -> new SPPStepResult(1, 0, 1, true, 1, 1, -1, 2));
        assertThrows(IllegalArgumentException.class,
                () -> new SPPStepResult(
                        Long.MAX_VALUE, 0, 1, true, 1, 1, Long.MAX_VALUE, 1));
    }

    @Test
    void rejectsInvalidAcceptedCombinations() {
        assertThrows(IllegalArgumentException.class,
                () -> new SPPStepResult(1, 0, 1, true, 0, 0, 1, 0));
        assertThrows(IllegalArgumentException.class,
                () -> new SPPStepResult(1, 0, 1, true, 2, 1, 1, 0));
        assertThrows(IllegalArgumentException.class,
                () -> new SPPStepResult(1, 0, 1, true, 1, 1, 0, 1));
    }

    @Test
    void rejectsInvalidRejectedCombinations() {
        assertThrows(IllegalArgumentException.class,
                () -> new SPPStepResult(1, 0, 1, false, 0, 0, 0, 1));
        assertThrows(IllegalArgumentException.class,
                () -> new SPPStepResult(1, 0, 1, false, -1, 1, 0, 1));
        assertThrows(IllegalArgumentException.class,
                () -> new SPPStepResult(1, 0, 1, false, -1, 0, 1, 0));
    }

    @Test
    void permitsCountersFromEarlierRequests() {
        assertDoesNotThrow(() -> new SPPStepResult(5, 0, 1, true, 1, 1, 3, 2));
        assertDoesNotThrow(() -> new SPPStepResult(5, 0, 1, false, -1, 0, 2, 3));
    }
}
