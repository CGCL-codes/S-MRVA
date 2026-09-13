
package testcode.sqli;

import org.springframework.dao.DataAccessException;
import org.springframework.jdbc.core.JdbcTemplate;

public class SpringJdbcTemplate {
    public void queryForList(JdbcTemplate jdbcTemplate, String sql) throws DataAccessException {
        // ruleid:spring-sqli
        jdbcTemplate.queryForList(sql, UserEntity.class);
    }
}
