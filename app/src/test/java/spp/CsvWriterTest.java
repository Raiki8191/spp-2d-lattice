package spp;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.junit.jupiter.api.Assertions.assertTrue;

import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.List;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.io.TempDir;

class CsvWriterTest {
    private static final String EXPECTED_HEADER =
            "run,L,C,step,removed_edges,remaining_edges,removed_edge_fraction,"
                    + "largest_cluster_size,largest_cluster_fraction,"
                    + "second_largest_cluster_size,mean_cluster_size,"
                    + "accepted_requests,rejected_requests,seed";

    @TempDir Path temporaryDirectory;

    @Test
    void createsParentDirectoriesAndWritesUtf8HeaderAndRow() throws IOException {
        Path path = temporaryDirectory.resolve("nested/results.csv");
        SPPResult result = result(2, 101L);

        try (CsvWriter writer = CsvWriter.create(path)) {
            writer.write(result);
        }

        List<String> lines = Files.readAllLines(path, StandardCharsets.UTF_8);
        assertEquals(EXPECTED_HEADER, lines.get(0));
        assertEquals(
                "2,2,3,1,1,3,0.25,4,1.0,0,0.0,1,0,101",
                lines.get(1));
        assertEquals(14, lines.get(1).split(",", -1).length);
    }

    @Test
    void writesMultipleRowsBeforeClose() throws IOException {
        Path path = temporaryDirectory.resolve("multiple.csv");

        try (CsvWriter writer = CsvWriter.create(path)) {
            writer.write(result(0, 10L));
            writer.write(result(1, 11L));
            writer.flush();
        }

        List<String> lines = Files.readAllLines(path, StandardCharsets.UTF_8);
        assertEquals(3, lines.size());
        assertTrue(lines.get(1).startsWith("0,"));
        assertTrue(lines.get(2).startsWith("1,"));
    }

    @Test
    void createOverwritesExistingFileWithOneHeader() throws IOException {
        Path path = temporaryDirectory.resolve("overwrite.csv");
        Files.writeString(path, "old content", StandardCharsets.UTF_8);

        try (CsvWriter writer = CsvWriter.create(path)) {
            writer.write(result(0, 1L));
        }

        List<String> lines = Files.readAllLines(path, StandardCharsets.UTF_8);
        assertEquals(2, lines.size());
        assertEquals(1, lines.stream().filter(EXPECTED_HEADER::equals).count());
        assertFalse(lines.contains("old content"));
    }

    @Test
    void appendDoesNotDuplicateExistingHeader() throws IOException {
        Path path = temporaryDirectory.resolve("append.csv");
        try (CsvWriter writer = CsvWriter.create(path)) {
            writer.write(result(0, 1L));
        }
        try (CsvWriter writer = CsvWriter.append(path)) {
            writer.write(result(1, 2L));
        }

        List<String> lines = Files.readAllLines(path, StandardCharsets.UTF_8);
        assertEquals(3, lines.size());
        assertEquals(1, lines.stream().filter(EXPECTED_HEADER::equals).count());
    }

    @Test
    void appendWritesHeaderForAbsentAndEmptyFiles() throws IOException {
        Path absent = temporaryDirectory.resolve("absent.csv");
        try (CsvWriter writer = CsvWriter.append(absent)) {
            writer.write(result(0, 1L));
        }

        Path empty = temporaryDirectory.resolve("empty.csv");
        Files.createFile(empty);
        try (CsvWriter writer = CsvWriter.append(empty)) {
            writer.write(result(0, 1L));
        }

        assertEquals(EXPECTED_HEADER, Files.readAllLines(absent).get(0));
        assertEquals(EXPECTED_HEADER, Files.readAllLines(empty).get(0));
    }

    @Test
    void closePersistsBufferedContent() throws IOException {
        Path path = temporaryDirectory.resolve("closed.csv");
        CsvWriter writer = CsvWriter.create(path);
        writer.write(result(0, 1L));
        writer.close();

        assertEquals(2, Files.readAllLines(path, StandardCharsets.UTF_8).size());
        assertThrows(IOException.class, () -> writer.write(result(1, 2L)));
    }

    @Test
    void rejectsNullPathAndResult() throws IOException {
        assertThrows(IllegalArgumentException.class, () -> CsvWriter.create(null));
        assertThrows(IllegalArgumentException.class, () -> CsvWriter.append(null));

        try (CsvWriter writer = CsvWriter.create(temporaryDirectory.resolve("null.csv"))) {
            assertThrows(IllegalArgumentException.class, () -> writer.write(null));
        }
    }

    @Test
    void propagatesIoErrors() {
        assertThrows(IOException.class, () -> CsvWriter.create(temporaryDirectory));
        assertThrows(IOException.class, () -> CsvWriter.append(temporaryDirectory));
    }

    private static SPPResult result(int run, long seed) {
        return new SPPResult(
                run, 2, 3, 1, 1, 3, 0.25, 4, 1.0, 0, 0.0, 1, 0, seed);
    }
}
