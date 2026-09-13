
import java.lang.Runtime;

class Cls {
    public void test5() {
        // ruleid: weak-ssl-context
        SSLContext ctx = SSLContext.getInstance("TLSv1.1");
    }
}
