
package testcode.sqli;

import org.springframework.dao.DataAccessException;
import org.springframework.jdbc.core.JdbcTemplate;

public class SpringJdbcTemplate {
    public void queryForRowSet(JdbcTemplate jdbcTemplate, String sql) throws DataAccessException {
        // ruleid:spring-sqli
        jdbcTemplate.queryForRowSet(sql, new Object[0]);
    }
}
