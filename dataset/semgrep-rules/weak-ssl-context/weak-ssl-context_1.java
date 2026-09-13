
import java.lang.Runtime;

class Cls {
    public void test2() {
        // ruleid: weak-ssl-context
        SSLContext ctx = SSLContext.getInstance("TLS");
    }
}
