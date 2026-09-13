
package testcode.sqli;

import javax.jdo.Extent;
import javax.jdo.PersistenceManager;

public class JdoSql {
    public void testJdoQueriesAdditionalMethodSig(String input) {
        PersistenceManager pm = getPM();
        // ok: jdo-sqli
        pm.newQuery((Extent) null,"id == 1");
    }
}
