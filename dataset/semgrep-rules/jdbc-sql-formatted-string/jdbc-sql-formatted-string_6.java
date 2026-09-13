
import java.lang.Runtime;
import org.springframework.jdbc.core.JdbcTemplate;

class TestClass {
    public void safe(String paramName) {
        JdbcTemplate jdbc = new JdbcTemplate();
        // ok:jdbc-sql-formatted-string
        int count = jdbc.queryForObject("select count(*) from Users where name = ?", Integer.class, paramName);
    }
}
