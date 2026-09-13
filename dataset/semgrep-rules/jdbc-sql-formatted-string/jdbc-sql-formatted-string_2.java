
import java.lang.Runtime;
import org.springframework.jdbc.core.JdbcTemplate;

class TestClass {
    public void unsafe_jdbc_queryForObject_3(String paramName) {
        JdbcTemplate jdbc = new JdbcTemplate();
        // ruleid:jdbc-sql-formatted-string
        StringBuilder query = new StringBuilder("select count(*) from Users");
        query.append( "where name = '"+paramName+"'");
        int count = jdbc.queryForObject(query, Integer.class);
    }
}
