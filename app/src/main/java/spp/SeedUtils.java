package spp;

/** Deterministic seed derivation for independent simulation random streams. */
public final class SeedUtils {
    private static final long PAIR_STREAM_CONSTANT = 0x504149525F535452L;
    private static final long PATH_STREAM_CONSTANT = 0x504154485F535452L;

    private SeedUtils() {}

    public static long runSeed(long baseSeed, int run) {
        if (run < 0) {
            throw new IllegalArgumentException("run must be non-negative");
        }
        return mix64(baseSeed + run);
    }

    public static long pairSeed(long runSeed) {
        return mix64(runSeed ^ PAIR_STREAM_CONSTANT);
    }

    public static long pathSeed(long runSeed) {
        return mix64(runSeed ^ PATH_STREAM_CONSTANT);
    }

    /** SplitMix64 finalizer. All operations intentionally use Java's wrapping long arithmetic. */
    public static long mix64(long value) {
        long mixed = value;
        mixed = (mixed ^ (mixed >>> 30)) * 0xBF58476D1CE4E5B9L;
        mixed = (mixed ^ (mixed >>> 27)) * 0x94D049BB133111EBL;
        return mixed ^ (mixed >>> 31);
    }
}
