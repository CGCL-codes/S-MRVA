
package testcode.sqli;

import org.springframework.dao.DataAccessException;
import org.springframework.jdbc.core.JdbcTemplate;

public class SpringJdbcTemplate {
    public void query4(JdbcTemplate jdbcTemplate, String input) throws DataAccessException {
        String sql = "select * from Users where name = '%s'";
        // ruleid:spring-sqli
        jdbcTemplate.execute(String.format(sql,input));
    }
}
