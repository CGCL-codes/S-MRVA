
package testcode.sqli;

import org.springframework.dao.DataAccessException;
import org.springframework.jdbc.core.JdbcTemplate;
import java.util.ArrayList;

public class SpringJdbcTemplate {
    public void queryBatchUpdate(JdbcTemplate jdbcTemplate, String sql, String taintedString) throws DataAccessException {
        // ruleid:spring-sqli
        jdbcTemplate.batchUpdate(sql, new ArrayList<Object[]>());
    }
}
