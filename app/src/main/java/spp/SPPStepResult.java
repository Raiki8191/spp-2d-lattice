package spp;

/** Immutable outcome of one processed SPP request. */
public record SPPStepResult(
        long step,
        int source,
        int target,
        boolean accepted,
        int pathLength,
        int removedEdgeCount,
        long acceptedRequests,
        long rejectedRequests) {

    public SPPStepResult {
        if (step < 1) {
            throw new IllegalArgumentException("step must be at least 1");
        }
        if (source < 0 || target < 0) {
            throw new IllegalArgumentException("source and target must be non-negative");
        }
        if (source == target) {
            throw new IllegalArgumentException("source and target must be different");
        }
        if (acceptedRequests < 0 || rejectedRequests < 0) {
            throw new IllegalArgumentException("request counters must be non-negative");
        }

        long requestCount;
        try {
            requestCount = Math.addExact(acceptedRequests, rejectedRequests);
        } catch (ArithmeticException e) {
            throw new IllegalArgumentException("request counter sum overflows long", e);
        }
        if (requestCount != step) {
            throw new IllegalArgumentException(
                    "acceptedRequests + rejectedRequests must equal step");
        }

        if (accepted) {
            if (pathLength < 1) {
                throw new IllegalArgumentException("accepted result requires a positive pathLength");
            }
            if (removedEdgeCount != pathLength) {
                throw new IllegalArgumentException(
                        "accepted result requires removedEdgeCount == pathLength");
            }
            if (acceptedRequests < 1) {
                throw new IllegalArgumentException(
                        "accepted result requires at least one accepted request");
            }
        } else {
            if (pathLength != -1) {
                throw new IllegalArgumentException("rejected result requires pathLength == -1");
            }
            if (removedEdgeCount != 0) {
                throw new IllegalArgumentException("rejected result cannot remove edges");
            }
            if (rejectedRequests < 1) {
                throw new IllegalArgumentException(
                        "rejected result requires at least one rejected request");
            }
        }
    }
}
