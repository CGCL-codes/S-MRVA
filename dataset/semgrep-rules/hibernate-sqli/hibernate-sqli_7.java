
package testcode.sqli;

import org.hibernate.Criteria;
import org.hibernate.Session;
import org.hibernate.SessionFactory;
import org.hibernate.criterion.Restrictions;
import org.hibernate.type.StandardBasicTypes;
import org.hibernate.type.Type;

public class HibernateSql {

    public void testQueries(SessionFactory sessionFactory, String input) {

        Session session = sessionFactory.openSession();

        Criteria criteria = session.createCriteria(UserEntity.class);

        final String localSql = "select * from TestEntity " + localSafe;
        // ok: hibernate-sqli
        session.createSQLQuery(localSql);
    }
}
