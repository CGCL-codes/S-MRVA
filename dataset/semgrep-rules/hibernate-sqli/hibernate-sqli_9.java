
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

        // ok: hibernate-sqli
        criteria.add(Restrictions.sqlRestriction("param1  = ? and param2 = ?", new String[] {input}, new Type[] {StandardBasicTypes.STRING}));
    }
}
