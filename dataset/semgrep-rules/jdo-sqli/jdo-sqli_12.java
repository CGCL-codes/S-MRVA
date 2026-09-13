
package testcode.sqli;

import javax.jdo.PersistenceManager;

public class JdoSql {
    public void testJdoQueriesAdditionalMethodSig(String input) {
        PersistenceManager pm = getPM();
        // ruleid: jdo-sqli
        pm.newQuery(UserEntity.class,"id == "+ input);
    }
}
