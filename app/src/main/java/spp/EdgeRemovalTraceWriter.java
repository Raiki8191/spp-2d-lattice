package spp;

import java.io.BufferedWriter;
import java.io.Closeable;
import java.io.IOException;
import java.io.UncheckedIOException;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.StandardOpenOption;
import java.util.HashMap;
import java.util.HashSet;
import java.util.Map;
import java.util.Set;

/** Streams accepted-request edge removals to a deterministic UTF-8 CSV trace. */
public final class EdgeRemovalTraceWriter implements Closeable {
    public static final String HEADER =
            "run,edge_order,step,edge_index_in_request,path_length,edge_id,source,target,seed";

    private final BufferedWriter writer;
    private final Map<Integer, Long> nextEdgeOrder = new HashMap<>();
    private final Map<Integer, Set<Integer>> seenEdgeIds = new HashMap<>();

    private EdgeRemovalTraceWriter(BufferedWriter writer) {
        this.writer = writer;
    }

    /** Creates a new trace, replacing any existing file. */
    public static EdgeRemovalTraceWriter create(Path path) throws IOException {
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
        return new EdgeRemovalTraceWriter(writer);
    }

    /** Returns an observer bound to one run and its recorded run seed. */
    public EdgeRemovalObserver observerForRun(int run, long seed) {
        if (run < 0) {
            throw new IllegalArgumentException("run must be non-negative");
        }
        return (step, source, target, path) -> writeAccepted(run, seed, step, source, target, path);
    }

    private void writeAccepted(
            int run,
            long seed,
            long step,
            int source,
            int target,
            ShortestPathResult path) {
        if (path == null) {
            throw new IllegalArgumentException("path must not be null");
        }
        long edgeOrder = nextEdgeOrder.getOrDefault(run, 0L);
        Set<Integer> seen = seenEdgeIds.computeIfAbsent(run, ignored -> new HashSet<>());
        int[] edgeIds = path.edgeIds();
        for (int edgeIndex = 0; edgeIndex < edgeIds.length; edgeIndex++) {
            int edgeId = edgeIds[edgeIndex];
            if (!seen.add(edgeId)) {
                throw new IllegalStateException(
                        "edge_id appears more than once in run " + run + ": " + edgeId);
            }
            try {
                writer.write(Integer.toString(run));
                writer.write(',' + Long.toString(edgeOrder));
                writer.write(',' + Long.toString(step));
                writer.write(',' + Integer.toString(edgeIndex));
                writer.write(',' + Integer.toString(path.distance()));
                writer.write(',' + Integer.toString(edgeId));
                writer.write(',' + Integer.toString(source));
                writer.write(',' + Integer.toString(target));
                writer.write(',' + Long.toString(seed));
                writer.newLine();
            } catch (IOException error) {
                throw new UncheckedIOException(error);
            }
            edgeOrder++;
        }
        nextEdgeOrder.put(run, edgeOrder);
    }

    @Override
    public void close() throws IOException {
        writer.close();
    }
}
