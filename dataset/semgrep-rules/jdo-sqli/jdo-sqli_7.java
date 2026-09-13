
package testcode.sqli;

import javax.jdo.PersistenceManager;

public class JdoSql {
    public void testJdoQueries(String input) {
        PersistenceManager pm = getPM();
        // ok: jdo-sqli
        pm.newQuery("select * from Config");
    }
}
