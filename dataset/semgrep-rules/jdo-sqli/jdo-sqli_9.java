
package testcode.sqli;

import javax.jdo.PersistenceManager;

public class JdoSql {
    public void testJdoQueries(String input) {
        PersistenceManager pm = getPM();
        final String query = "select * from Config";
        // ok: jdo-sqli
        pm.newQuery("sql", query);
    }
}
