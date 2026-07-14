package spp;

/** Machine-readable reason why one simulation run stopped. */
public enum TerminationReason {
    TRANSITION_WINDOW_COMPLETE,
    ALL_EDGES_REMOVED,
    MAX_STEPS
}
