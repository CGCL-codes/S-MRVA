
package testcode.sqli;

import org.springframework.dao.DataAccessException;
import org.springframework.jdbc.core.JdbcTemplate;

public class SpringJdbcTemplate {
    public void queryForLong(JdbcTemplate jdbcTemplate, String sql) throws DataAccessException {
        // ruleid:spring-sqli
        jdbcTemplate.queryForLong(sql, new Object[0]);
    }
}
