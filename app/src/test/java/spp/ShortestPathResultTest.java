package spp;

import org.junit.jupiter.api.Test;

import static org.junit.jupiter.api.Assertions.assertArrayEquals;
import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertThrows;

class ShortestPathResultTest {
    @Test
    void defensivelyCopiesInputAndReturnedArrays() {
        int[] input = {3, 7};
        ShortestPathResult result = new ShortestPathResult(2, input);

        input[0] = 99;
        int[] returned = result.edgeIds();
        returned[1] = 88;

        assertArrayEquals(new int[] {3, 7}, result.edgeIds());
    }

    @Test
    void requiresEdgeCountToEqualDistance() {
        assertThrows(IllegalArgumentException.class,
                () -> new ShortestPathResult(2, new int[] {1}));
        assertThrows(IllegalArgumentException.class,
                () -> new ShortestPathResult(-1, new int[0]));
        assertThrows(IllegalArgumentException.class,
                () -> new ShortestPathResult(0, null));
        assertThrows(IllegalArgumentException.class,
                () -> new ShortestPathResult(1, new int[] {-1}));
    }

    @Test
    void exposesDistanceAndPathCopy() {
        ShortestPathResult result = new ShortestPathResult(1, new int[] {4});

        assertEquals(1, result.distance());
        assertArrayEquals(new int[] {4}, result.edgeIds());
    }
}
