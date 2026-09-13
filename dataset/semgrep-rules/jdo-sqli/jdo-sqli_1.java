
package testcode.sqli;

import javax.jdo.PersistenceManager;
import javax.jdo.Query;

public class JdoSqlFilter {
    public void testJdoSafeFilter(String filterValue) {
        PersistenceManager pm = getPM();
        Query q = pm.newQuery(UserEntity.class);
        // ok: jdo-sqli
        q.setFilter("id == 1");
    }
}
