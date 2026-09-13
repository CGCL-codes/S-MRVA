
package testcode.sqli;

import org.springframework.jdbc.core.JdbcOperations;
import java.sql.Types;
import java.util.ArrayList;

public class SpringBatchUpdateUtils {
    JdbcOperations jdbcOperations;

    public void queryNamedParameterBatchUpdateUtilsSafe() {
        String sql = "UPDATE Users SET name = 'safe' where id = 1";
        // ok:spring-sqli
        NamedParameterBatchUpdateUtils.executeBatchUpdate(sql, new ArrayList<Object[]>(), new int[]{Types.INTEGER}, jdbcOperations);
    }
}
