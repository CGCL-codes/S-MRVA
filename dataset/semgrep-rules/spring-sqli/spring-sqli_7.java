
package testcode.sqli;

import org.springframework.dao.DataAccessException;
import org.springframework.jdbc.core.JdbcTemplate;

public class SpringJdbcTemplate {
    public void querySafe(JdbcTemplate jdbcTemplate, String input) throws DataAccessException {
        String sql = "select * from Users where name = '1'";
        // ok:spring-sqli
        jdbcTemplate.execute(sql);
    }
}
