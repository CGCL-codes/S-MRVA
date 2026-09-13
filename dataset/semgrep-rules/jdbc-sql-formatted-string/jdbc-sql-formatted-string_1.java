
import java.lang.Runtime;
import org.springframework.jdbc.core.JdbcTemplate;

class TestClass {
    public void unsafe_jdbc_queryForObject_2(String paramName) {
        JdbcTemplate jdbc = new JdbcTemplate();
        // ruleid:jdbc-sql-formatted-string
        String query = "select count(*) from Users where name = '"+paramName+"'";
        int count = jdbc.queryForObject(query, Integer.class);
    }
}
