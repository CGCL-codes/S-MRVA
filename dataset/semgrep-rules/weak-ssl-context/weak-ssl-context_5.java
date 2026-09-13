
import java.lang.Runtime;

class Cls {
    public void test6() {
        // ok: weak-ssl-context
        SSLContext ctx = SSLContext.getInstance("TLSv1.2");
    }
}
