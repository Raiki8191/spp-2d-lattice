package spp;

import org.junit.jupiter.api.Test;

import static org.junit.jupiter.api.Assertions.assertEquals;

class AppTest {
    @Test
    void returnsStartupMessage() {
        assertEquals("SPP project is ready.", App.message());
    }
}
