package spp;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertNotEquals;
import static org.junit.jupiter.api.Assertions.assertThrows;

import java.util.HashSet;
import java.util.Set;
import org.junit.jupiter.api.Test;

class SeedUtilsTest {
    @Test
    void sameInputsProduceSameSeeds() {
        long firstRunSeed = SeedUtils.runSeed(42L, 7);
        long secondRunSeed = SeedUtils.runSeed(42L, 7);

        assertEquals(firstRunSeed, secondRunSeed);
        assertEquals(SeedUtils.pairSeed(firstRunSeed), SeedUtils.pairSeed(secondRunSeed));
        assertEquals(SeedUtils.pathSeed(firstRunSeed), SeedUtils.pathSeed(secondRunSeed));
    }

    @Test
    void differentRunNumbersProduceDifferentRunSeeds() {
        assertNotEquals(SeedUtils.runSeed(42L, 0), SeedUtils.runSeed(42L, 1));
    }

    @Test
    void pairAndPathStreamsUseDifferentSeeds() {
        long runSeed = SeedUtils.runSeed(42L, 0);
        assertNotEquals(SeedUtils.pairSeed(runSeed), SeedUtils.pathSeed(runSeed));
    }

    @Test
    void multipleRunsHaveNoSeedCollisions() {
        Set<Long> runSeeds = new HashSet<>();
        Set<Long> pairSeeds = new HashSet<>();
        Set<Long> pathSeeds = new HashSet<>();

        for (int run = 0; run < 1_000; run++) {
            long runSeed = SeedUtils.runSeed(Long.MAX_VALUE - 10, run);
            runSeeds.add(runSeed);
            pairSeeds.add(SeedUtils.pairSeed(runSeed));
            pathSeeds.add(SeedUtils.pathSeed(runSeed));
        }

        assertEquals(1_000, runSeeds.size());
        assertEquals(1_000, pairSeeds.size());
        assertEquals(1_000, pathSeeds.size());
    }

    @Test
    void rejectsNegativeRunNumber() {
        assertThrows(IllegalArgumentException.class, () -> SeedUtils.runSeed(42L, -1));
    }
}
