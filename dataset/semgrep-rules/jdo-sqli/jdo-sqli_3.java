
package testcode.sqli;

import javax.jdo.PersistenceManager;
import javax.jdo.Query;

public class JdoSqlFilter {
    private static final String FIELD_TEST = "test";
    
    public void testJdoUnsafeGrouping(String groupByField) {
        PersistenceManager pm = getPM();
        Query q = pm.newQuery(UserEntity.class);
        // ruleid: jdo-sqli
        q.setGrouping(groupByField);
    }
}
