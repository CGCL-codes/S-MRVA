
package testcode.sqli;

import org.springframework.dao.DataAccessException;
import org.springframework.jdbc.core.JdbcTemplate;

public class SpringJdbcTemplate {
    public void query2(JdbcTemplate jdbcTemplate, String input) throws DataAccessException {
        String sql = "select * from Users where name = '" + input + "'";
        // ruleid:spring-sqli
        jdbcTemplate.execute(sql);
    }
}
