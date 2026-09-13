
import java.lang.Runtime;

class Cls {
    public String getSslContext() {
        return "Anything";
    }

    public void test8() {
        // ok: weak-ssl-context
        SSLContext ctx = SSLContext.getInstance(getSslContext());
    }
}
