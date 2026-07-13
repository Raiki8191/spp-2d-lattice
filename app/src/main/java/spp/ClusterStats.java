package spp;

import java.util.Objects;

/** Immutable statistics for the connected components of a lattice. */
public record ClusterStats(
        int componentCount,
        int largestClusterSize,
        int secondLargestClusterSize,
        double meanClusterSize,
        int[] componentSizes) {

    public ClusterStats {
        Objects.requireNonNull(componentSizes, "componentSizes must not be null");
        componentSizes = componentSizes.clone();

        if (componentCount < 1 || componentCount != componentSizes.length) {
            throw new IllegalArgumentException(
                    "componentCount must be positive and match componentSizes length");
        }

        for (int i = 0; i < componentSizes.length; i++) {
            if (componentSizes[i] < 1) {
                throw new IllegalArgumentException("component sizes must be positive");
            }
            if (i > 0 && componentSizes[i - 1] < componentSizes[i]) {
                throw new IllegalArgumentException("componentSizes must be in descending order");
            }
        }

        if (largestClusterSize != componentSizes[0]) {
            throw new IllegalArgumentException("largestClusterSize must match the first component size");
        }

        int expectedSecondLargest = componentCount == 1 ? 0 : componentSizes[1];
        if (secondLargestClusterSize != expectedSecondLargest) {
            throw new IllegalArgumentException(
                    "secondLargestClusterSize does not match componentSizes");
        }

        double expectedMean = calculateMeanClusterSize(componentSizes);
        if (Double.compare(meanClusterSize, expectedMean) != 0) {
            throw new IllegalArgumentException(
                    "meanClusterSize must exclude exactly one largest component");
        }
    }

    @Override
    public int[] componentSizes() {
        return componentSizes.clone();
    }

    static double calculateMeanClusterSize(int[] descendingComponentSizes) {
        if (descendingComponentSizes.length == 1) {
            return 0.0;
        }

        double squaredSizeSum = 0.0;
        long sizeSum = 0L;
        for (int i = 1; i < descendingComponentSizes.length; i++) {
            long size = descendingComponentSizes[i];
            squaredSizeSum += (double) size * size;
            sizeSum += size;
        }
        return squaredSizeSum / sizeSum;
    }
}
