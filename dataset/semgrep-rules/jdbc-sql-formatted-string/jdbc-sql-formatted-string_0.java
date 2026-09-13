
import java.lang.Runtime;
import org.springframework.jdbc.core.JdbcTemplate;

class TestClass {
    public void unsafe_jdbc_queryForObject_1(String paramName) {
        JdbcTemplate jdbc = new JdbcTemplate();
        // ruleid:jdbc-sql-formatted-string
        int count = jdbc.queryForObject("select count(*) from Users where name = '"+paramName+"'", Integer.class);
    }
}
