
import java.security.*;

public class NoReturnNoException {
    public void somemethod() {
        // Anonymous class
        // ruleid: do-privileged-use
        AccessController.doPrivileged(new PrivilegedAction<Void>() {
            public Void run() {
                // Privileged code goes here, for example:
                System.loadLibrary("awt");
                return null; // nothing to return
            }
        });
    }
}
