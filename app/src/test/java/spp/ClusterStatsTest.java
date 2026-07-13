package spp;

import static org.junit.jupiter.api.Assertions.assertArrayEquals;
import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertThrows;

import org.junit.jupiter.api.Test;

class ClusterStatsTest {
    @Test
    void calculatesMeanForFourTwoOne() {
        ClusterStats stats = new ClusterStats(3, 4, 2, 5.0 / 3.0, new int[] {4, 2, 1});

        assertEquals(5.0 / 3.0, stats.meanClusterSize());
    }

    @Test
    void excludesOnlyOneOfTiedLargestComponents() {
        ClusterStats stats = new ClusterStats(3, 3, 3, 2.5, new int[] {3, 3, 1});

        assertEquals(3, stats.largestClusterSize());
        assertEquals(3, stats.secondLargestClusterSize());
        assertEquals(2.5, stats.meanClusterSize());
    }

    @Test
    void singleComponentHasZeroSecondLargestAndMean() {
        ClusterStats stats = new ClusterStats(1, 9, 0, 0.0, new int[] {9});

        assertEquals(0, stats.secondLargestClusterSize());
        assertEquals(0.0, stats.meanClusterSize());
    }

    @Test
    void defensivelyCopiesComponentSizes() {
        int[] input = {4, 2, 1};
        ClusterStats stats = new ClusterStats(3, 4, 2, 5.0 / 3.0, input);
        input[0] = 99;

        int[] returned = stats.componentSizes();
        returned[0] = 88;

        assertArrayEquals(new int[] {4, 2, 1}, stats.componentSizes());
    }

    @Test
    void rejectsNullComponentSizes() {
        assertThrows(NullPointerException.class, () -> new ClusterStats(1, 1, 0, 0.0, null));
    }

    @Test
    void rejectsCountThatDoesNotMatchArray() {
        assertThrows(
                IllegalArgumentException.class,
                () -> new ClusterStats(2, 1, 0, 0.0, new int[] {1}));
    }

    @Test
    void rejectsNonDescendingSizes() {
        assertThrows(
                IllegalArgumentException.class,
                () -> new ClusterStats(2, 1, 2, 2.0, new int[] {1, 2}));
    }

    @Test
    void rejectsNonPositiveSize() {
        assertThrows(
                IllegalArgumentException.class,
                () -> new ClusterStats(2, 1, 0, 0.0, new int[] {1, 0}));
    }

    @Test
    void rejectsInconsistentDerivedStatistics() {
        assertThrows(
                IllegalArgumentException.class,
                () -> new ClusterStats(3, 3, 2, 5.0 / 3.0, new int[] {4, 2, 1}));
        assertThrows(
                IllegalArgumentException.class,
                () -> new ClusterStats(3, 4, 1, 5.0 / 3.0, new int[] {4, 2, 1}));
        assertThrows(
                IllegalArgumentException.class,
                () -> new ClusterStats(3, 4, 2, 1.0, new int[] {4, 2, 1}));
    }
}
