
package testcode.sqli;

import org.springframework.dao.DataAccessException;
import org.springframework.jdbc.core.JdbcTemplate;
import java.sql.Types;

public class SpringJdbcTemplate {
    public void queryForMap(JdbcTemplate jdbcTemplate, String sql) throws DataAccessException {
        // ruleid:spring-sqli
        jdbcTemplate.queryForMap(sql, new Object[0], new int[]{Types.VARCHAR});
    }
}
