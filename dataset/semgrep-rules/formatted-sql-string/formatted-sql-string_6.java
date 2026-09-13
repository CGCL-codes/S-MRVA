
package sql.injection;

import javax.persistence.EntityManager;
import javax.persistence.TypedQuery;
import java.util.List;
import java.util.stream.Collectors;

public class SqlExample2 {
    public List<AccountDTO> findAccountsById(String id) {
        String jql = "from Account where id = '" + id + "'";
        EntityManager em = emfactory.createEntityManager();
        // ruleid:formatted-sql-string
        TypedQuery<Account> q = em.createQuery(jql, Account.class);
        return q.getResultList()
        .stream()
        .map(this::toAccountDTO)
        .collect(Collectors.toList());
    }
}
