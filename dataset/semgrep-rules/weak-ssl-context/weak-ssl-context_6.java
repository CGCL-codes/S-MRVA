
import java.lang.Runtime;

class Cls {
    public void test7() {
        // ok: weak-ssl-context
        SSLContext ctx = SSLContext.getInstance("TLSv1.3");
    }
}
