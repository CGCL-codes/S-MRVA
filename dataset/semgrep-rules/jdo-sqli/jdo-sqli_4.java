
package testcode.sqli;

import javax.jdo.PersistenceManager;
import javax.jdo.Query;

public class JdoSqlFilter {
    private static final String FIELD_TEST = "test";
    
    public void testJdoSafeGrouping() {
        PersistenceManager pm = getPM();
        Query q = pm.newQuery(UserEntity.class);
        // ok: jdo-sqli
        q.setGrouping(FIELD_TEST);
    }
}
