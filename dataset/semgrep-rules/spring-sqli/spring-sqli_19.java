
package testcode.sqli;

import org.springframework.dao.DataAccessException;
import org.springframework.jdbc.core.JdbcTemplate;
import java.util.ArrayList;
import java.util.Arrays;
import java.sql.Types;

public class SpringJdbcTemplate {
    public void queryBatchUpdate(JdbcTemplate jdbcTemplate, String sql, String taintedString) throws DataAccessException {
        // ok:spring-sqli
        jdbcTemplate.batchUpdate("SELECT foo FROM bar WHERE baz = 'biz'", new ArrayList<Object[]>(Arrays.asList(new Object[] {taintedString})));
    }
}
