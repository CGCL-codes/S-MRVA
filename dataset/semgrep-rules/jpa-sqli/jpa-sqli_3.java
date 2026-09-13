
package testcode.sqli;

import javax.persistence.EntityManager;
import javax.persistence.TypedQuery;

public class JpaSql {

    public UserEntity getFirstAlt2(EntityManager em) {
        final String sql = "select * from Users";
        // ok:jpa-sqli
        TypedQuery<UserEntity> q = (TypedQuery<UserEntity>) em.createQuery(sql);
        return q.getSingleResult();
    }
}
