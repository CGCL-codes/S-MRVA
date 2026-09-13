
package testcode.sqli;

import javax.jdo.PersistenceManager;

public class JdoSql {
    public void testJdoQueries(String input) {
        PersistenceManager pm = getPM();
        // ruleid: jdo-sqli
        pm.newQuery("select * from Users where name = " + input);
    }
}
