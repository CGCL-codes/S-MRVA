
package testcode.sqli;

import javax.persistence.EntityManager;
import javax.persistence.TypedQuery;

public class JpaSql {

    public UserEntity getFirst(EntityManager em) {
        // ok:jpa-sqli
        TypedQuery<UserEntity> q = em.createQuery(
                "select * from Users",
                UserEntity.class);
        return q.getSingleResult();
    }
}
