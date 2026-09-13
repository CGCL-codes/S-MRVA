
package testcode.sqli;

import javax.persistence.EntityManager;
import javax.persistence.TypedQuery;

public class JpaSql {

    public void getUserByUsernameAlt2(EntityManager em, String username) {
        // ruleid:jpa-sqli
        TypedQuery<UserEntity> q = em.createQuery(
                "select * from Users where name = '" + username + "'",
                UserEntity.class);

        UserEntity res = q.getSingleResult();
    }
}
