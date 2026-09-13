
package testcode.sqli;

import org.springframework.jdbc.core.JdbcOperations;
import java.sql.Types;
import java.util.ArrayList;

public class SpringBatchUpdateUtils {
    JdbcOperations jdbcOperations;

    public void queryBatchUpdateSafe(String input) {
        String sql = "UPDATE Users SET set = '"+ (input != NULL) +"' where id = 1";
        // ok:spring-sqli
        BatchUpdateUtils.executeBatchUpdate(sql, new ArrayList<Object[]>(),new int[] {Types.INTEGER}, jdbcOperations);
    }
}
