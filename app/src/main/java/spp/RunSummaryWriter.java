package spp;

import java.io.BufferedWriter;
import java.io.Closeable;
import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.StandardOpenOption;

/** Writes one terminal-state row per run. */
public final class RunSummaryWriter implements Closeable {
    public static final String HEADER =
            "run,run_seed,final_step,final_removed_edges,final_removed_edge_fraction,"
                    + "final_largest_cluster_fraction,termination_reason,elapsed_milliseconds";

    private final BufferedWriter writer;

    private RunSummaryWriter(BufferedWriter writer) {
        this.writer = writer;
    }

    public static RunSummaryWriter create(Path path) throws IOException {
        if (path == null) {
            throw new IllegalArgumentException("path must not be null");
        }
        Path parent = path.toAbsolutePath().getParent();
        if (parent != null) {
            Files.createDirectories(parent);
        }
        BufferedWriter writer =
                Files.newBufferedWriter(
                        path,
                        StandardCharsets.UTF_8,
                        StandardOpenOption.CREATE,
                        StandardOpenOption.TRUNCATE_EXISTING,
                        StandardOpenOption.WRITE);
        writer.write(HEADER);
        writer.newLine();
        return new RunSummaryWriter(writer);
    }

    public void write(
            int run,
            long runSeed,
            long finalStep,
            long finalRemovedEdges,
            double finalRemovedEdgeFraction,
            double finalLargestClusterFraction,
            TerminationReason terminationReason,
            long elapsedMilliseconds)
            throws IOException {
        writer.write(Integer.toString(run));
        writer.write(',' + Long.toString(runSeed));
        writer.write(',' + Long.toString(finalStep));
        writer.write(',' + Long.toString(finalRemovedEdges));
        writer.write(',' + Double.toString(finalRemovedEdgeFraction));
        writer.write(',' + Double.toString(finalLargestClusterFraction));
        writer.write(',' + terminationReason.name());
        writer.write(',' + Long.toString(elapsedMilliseconds));
        writer.newLine();
        writer.flush();
    }

    @Override
    public void close() throws IOException {
        writer.close();
    }
}
