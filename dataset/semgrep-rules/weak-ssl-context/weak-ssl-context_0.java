
import java.lang.Runtime;

class Cls {
    public void test1() {
        // ruleid: weak-ssl-context
        SSLContext ctx = SSLContext.getInstance("SSL");
    }
}
