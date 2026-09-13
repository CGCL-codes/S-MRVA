
package testcode.sqli;

import org.springframework.dao.DataAccessException;
import org.springframework.jdbc.core.JdbcTemplate;

public class SpringJdbcTemplate {
    public void query3(JdbcTemplate jdbcTemplate, String input) throws DataAccessException {
        // ruleid:spring-sqli
        jdbcTemplate.execute(String.format("select * from Users where name = '%s'",input));
    }
}
