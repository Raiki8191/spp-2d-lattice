package spp;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.junit.jupiter.api.Assertions.assertTrue;

import java.io.ByteArrayOutputStream;
import java.io.IOException;
import java.io.PrintStream;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.io.TempDir;

class ShortestPathPercolationTest {
    @TempDir Path temporaryDirectory;

    @Test
    void defaultConfigurationIsSmallAndDeterministic() {
        SPPConfig config = ShortestPathPercolation.createDefaultConfig();

        assertEquals(4, config.L());
        assertEquals(2, config.C());
        assertEquals(2, config.runs());
        assertEquals(20, config.maxSteps());
        assertEquals(5, config.measurementInterval());
        assertEquals(42L, config.baseSeed());
    }

    @Test
    void runsSmallConfigurationAndPrintsCompletionSummary() throws IOException {
        SPPConfig config =
                new SPPConfig(
                        3,
                        2,
                        1,
                        3,
                        1,
                        BoundaryCondition.OPEN,
                        42L,
                        temporaryDirectory);
        ByteArrayOutputStream bytes = new ByteArrayOutputStream();

        Path outputPath;
        try (PrintStream output = new PrintStream(bytes, true, StandardCharsets.UTF_8)) {
            outputPath = ShortestPathPercolation.run(config, output);
        }

        String message = bytes.toString(StandardCharsets.UTF_8);
        assertTrue(Files.isRegularFile(outputPath));
        assertTrue(message.contains("L=3"));
        assertTrue(message.contains("C=2"));
        assertTrue(message.contains("runs=1"));
        assertTrue(message.contains(outputPath.toAbsolutePath().toString()));
        assertTrue(message.contains("SPP experiment completed successfully."));
    }

    @Test
    void rejectsNullInputs() {
        SPPConfig config = ShortestPathPercolation.createDefaultConfig();
        assertThrows(
                IllegalArgumentException.class,
                () -> ShortestPathPercolation.run(null, System.out));
        assertThrows(
                IllegalArgumentException.class,
                () -> ShortestPathPercolation.run(config, null));
    }
}
