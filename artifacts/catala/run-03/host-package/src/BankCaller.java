import java.nio.file.Files;
import java.nio.file.Path;

/** Separate Java 17 caller, following the current project's library-host pattern. */
public final class BankCaller {
    private BankCaller() {}
    public static void main(String[] args) throws Exception {
        if (args.length != 1) throw new IllegalArgumentException("One typed request file required");
        System.out.println(CatalaPilotHost.evaluate(Files.readString(Path.of(args[0]))));
    }
}
