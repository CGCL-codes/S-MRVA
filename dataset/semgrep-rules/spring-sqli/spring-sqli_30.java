
package testcode.sqli;

import org.springframework.dao.DataAccessException;
import org.springframework.jdbc.core.JdbcTemplate;

public class SpringJdbcTemplate {
    public void querySamples(JdbcTemplate jdbcTemplate, String sql) throws DataAccessException {
        // ruleid:spring-sqli
        jdbcTemplate.query(sql, new TestRowCallbackHandler());
    }
}
