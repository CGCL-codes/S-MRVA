
import java.lang.Runtime;

class Cls {
    public void test3() {
        // ruleid: weak-ssl-context
        SSLContext ctx = SSLContext.getInstance("TLSv1");
    }
}
