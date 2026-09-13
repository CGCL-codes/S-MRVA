
import java.security.*;

public class NoReturnNoException {
    public void somemethod() {
        // Lambda expression
        // ruleid: do-privileged-use
        AccessController.doPrivileged((PrivilegedAction<Void>)
            () -> {
                // Privileged code goes here, for example:
                System.loadLibrary("awt");
                return null; // nothing to return
            }
        );
    }
}
