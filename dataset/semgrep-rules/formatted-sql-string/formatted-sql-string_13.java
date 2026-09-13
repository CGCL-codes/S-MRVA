
package sql.injection;

import javax.persistence.EntityManager;
import javax.persistence.criteria.CriteriaBuilder;
import javax.persistence.criteria.CriteriaQuery;
import java.util.List;

public class FalsePositiveCase {
    public List<Student> addWhere(String name, CriteriaQuery Query)
    {
        EntityManager em = emfactory.createEntityManager();
    	CriteriaBuilder criteriaBuilder = em.getCriteriaBuilder();
		// ok: formatted-sql-string
        List<Student> students = em.createQuery(Query.where(criteriaBuilder.equal(studentRoot.get("name"), name ))).getResultList();
        return students;
    }
}
