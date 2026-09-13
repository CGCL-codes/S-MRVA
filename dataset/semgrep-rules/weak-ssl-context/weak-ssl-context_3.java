
import java.lang.Runtime;

class Cls {
    public void test4() {
        // ruleid: weak-ssl-context
        SSLContext ctx = SSLContext.getInstance("SSLv3");
    }
}
