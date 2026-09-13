
package testcode.sqli;

import javax.jdo.PersistenceManager;
import javax.jdo.Query;

public class JdoSqlFilter {
    public void testJdoUnsafeFilter(String filterValue) {
        PersistenceManager pm = getPM();
        Query q = pm.newQuery(UserEntity.class);
        // ruleid: jdo-sqli
        q.setFilter("id == "+filterValue);
    }
}
