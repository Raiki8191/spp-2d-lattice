package spp;

/** Observes one accepted request after all selected path edges have been removed. */
@FunctionalInterface
public interface EdgeRemovalObserver {
    EdgeRemovalObserver NONE = (step, source, target, path) -> {};

    /** Receives an immutable shortest path whose edge IDs are in source-to-target order. */
    void edgesRemoved(long step, int source, int target, ShortestPathResult path);
}
