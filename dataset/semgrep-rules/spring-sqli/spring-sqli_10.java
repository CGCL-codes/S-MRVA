
package testcode.sqli;

import org.springframework.dao.DataAccessException;
import org.springframework.jdbc.core.JdbcTemplate;
import java.sql.PreparedStatementCallback;

public class SpringJdbcTemplate {
    public void queryExecute(JdbcTemplate jdbcTemplate, String sql) throws DataAccessException {
        // ruleid:spring-sqli
        jdbcTemplate.execute(sql, (PreparedStatementCallback) new TestCallableStatementCallback());
    }
}
