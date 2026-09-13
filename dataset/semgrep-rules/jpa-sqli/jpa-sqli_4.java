
package testcode.sqli;

import javax.persistence.EntityManager;
import javax.persistence.TypedQuery;

public class JpaSql {

    public void getUserWithNativeQueryUnsafe(EntityManager em, String password) {
        String sql = "select * from Users where user = 'admin' and password='"+password+"'";
        // ruleid:jpa-sqli
        em.createNativeQuery(sql);
        // ruleid:jpa-sqli
        em.createNativeQuery(sql,"testcode.sqli.UserEntity");
        // ruleid:jpa-sqli
        em.createNativeQuery(sql, UserEntity.class);
    }
}
