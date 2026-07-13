package spp;

public final class App {
    private static final String MESSAGE = "SPP project is ready.";

    private App() {
    }

    public static void main(String[] args) {
        System.out.println(message());
    }

    static String message() {
        return MESSAGE;
    }
}
