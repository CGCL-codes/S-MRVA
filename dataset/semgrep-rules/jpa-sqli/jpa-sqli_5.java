
package testcode.sqli;

import javax.persistence.EntityManager;
import javax.persistence.TypedQuery;

public class JpaSql {

    public void getUserWithNativeQuerySafe(EntityManager em) {
        String sql = "select * from Users where user = 'admin'";
        // ok:jpa-sqli
        em.createNativeQuery(sql);
        // ok:jpa-sqli
        em.createNativeQuery(sql,"testcode.sqli.UserEntity");
        // ok:jpa-sqli
        em.createNativeQuery(sql, UserEntity.class);
    }
}
