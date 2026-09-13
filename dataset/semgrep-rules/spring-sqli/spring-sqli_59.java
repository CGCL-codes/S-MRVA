
package testcode.sqli;

import org.springframework.jdbc.core.JdbcOperations;
import java.sql.Types;
import java.util.ArrayList;

public class SpringBatchUpdateUtils {
    JdbcOperations jdbcOperations;

    public void queryBatchUpdateUnsafe(String input) {
        String sql = "UPDATE Users SET name = '"+input+"' where id = 1";
        // ruleid:spring-sqli
        BatchUpdateUtils.executeBatchUpdate(sql, new ArrayList<Object[]>(),new int[] {Types.INTEGER}, jdbcOperations);
    }
}
