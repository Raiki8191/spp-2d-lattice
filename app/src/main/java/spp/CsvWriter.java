package spp;

import java.io.BufferedWriter;
import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.OpenOption;
import java.nio.file.Path;
import java.nio.file.StandardOpenOption;

/** Writes SPP measurement snapshots as UTF-8 CSV. */
public final class CsvWriter implements AutoCloseable {
    public static final String HEADER =
            "run,L,C,step,removed_edges,remaining_edges,removed_edge_fraction,"
                    + "largest_cluster_size,largest_cluster_fraction,"
                    + "second_largest_cluster_size,mean_cluster_size,"
                    + "accepted_requests,rejected_requests,seed";

    private final BufferedWriter writer;

    private CsvWriter(BufferedWriter writer) {
        this.writer = writer;
    }

    /** Creates or replaces a CSV file and immediately writes its header. */
    public static CsvWriter create(Path path) throws IOException {
        requirePath(path);
        createParentDirectories(path);
        return openWithHeader(
                path,
                StandardOpenOption.CREATE,
                StandardOpenOption.TRUNCATE_EXISTING,
                StandardOpenOption.WRITE);
    }

    /** Appends to a CSV file, writing a header only when the file is absent or empty. */
    public static CsvWriter append(Path path) throws IOException {
        requirePath(path);
        createParentDirectories(path);
        boolean needsHeader = !Files.exists(path) || Files.size(path) == 0L;
        BufferedWriter bufferedWriter =
                Files.newBufferedWriter(
                        path,
                        StandardCharsets.UTF_8,
                        StandardOpenOption.CREATE,
                        StandardOpenOption.APPEND,
                        StandardOpenOption.WRITE);
        if (!needsHeader) {
            return new CsvWriter(bufferedWriter);
        }
        try {
            writeHeader(bufferedWriter);
            return new CsvWriter(bufferedWriter);
        } catch (IOException exception) {
            try {
                bufferedWriter.close();
            } catch (IOException closeException) {
                exception.addSuppressed(closeException);
            }
            throw exception;
        }
    }

    public void write(SPPResult result) throws IOException {
        if (result == null) {
            throw new IllegalArgumentException("result must not be null");
        }

        writer.write(Integer.toString(result.run()));
        writer.write(',');
        writer.write(Integer.toString(result.L()));
        writer.write(',');
        writer.write(Integer.toString(result.C()));
        writer.write(',');
        writer.write(Long.toString(result.step()));
        writer.write(',');
        writer.write(Long.toString(result.removedEdges()));
        writer.write(',');
        writer.write(Long.toString(result.remainingEdges()));
        writer.write(',');
        writer.write(Double.toString(result.removedEdgeFraction()));
        writer.write(',');
        writer.write(Integer.toString(result.largestClusterSize()));
        writer.write(',');
        writer.write(Double.toString(result.largestClusterFraction()));
        writer.write(',');
        writer.write(Integer.toString(result.secondLargestClusterSize()));
        writer.write(',');
        writer.write(Double.toString(result.meanClusterSize()));
        writer.write(',');
        writer.write(Long.toString(result.acceptedRequests()));
        writer.write(',');
        writer.write(Long.toString(result.rejectedRequests()));
        writer.write(',');
        writer.write(Long.toString(result.seed()));
        writer.newLine();
    }

    public void flush() throws IOException {
        writer.flush();
    }

    @Override
    public void close() throws IOException {
        writer.close();
    }

    private static CsvWriter openWithHeader(Path path, OpenOption... options) throws IOException {
        BufferedWriter bufferedWriter =
                Files.newBufferedWriter(path, StandardCharsets.UTF_8, options);
        try {
            writeHeader(bufferedWriter);
            return new CsvWriter(bufferedWriter);
        } catch (IOException exception) {
            try {
                bufferedWriter.close();
            } catch (IOException closeException) {
                exception.addSuppressed(closeException);
            }
            throw exception;
        }
    }

    private static void writeHeader(BufferedWriter bufferedWriter) throws IOException {
        bufferedWriter.write(HEADER);
        bufferedWriter.newLine();
    }

    private static void createParentDirectories(Path path) throws IOException {
        Path parent = path.toAbsolutePath().getParent();
        if (parent != null) {
            Files.createDirectories(parent);
        }
    }

    private static void requirePath(Path path) {
        if (path == null) {
            throw new IllegalArgumentException("path must not be null");
        }
    }
}
