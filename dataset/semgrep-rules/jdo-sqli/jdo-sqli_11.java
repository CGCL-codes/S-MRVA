
package testcode.sqli;

import javax.jdo.PersistenceManager;
import java.util.ArrayList;

public class JdoSql {
    public void testJdoQueriesAdditionalMethodSig(String input) {
        PersistenceManager pm = getPM();
        // ok: jdo-sqli
        pm.newQuery(UserEntity.class,new ArrayList(),"id == 1");
    }
}
