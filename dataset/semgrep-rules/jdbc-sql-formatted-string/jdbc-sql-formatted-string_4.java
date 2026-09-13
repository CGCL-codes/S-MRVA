
import java.lang.Runtime;
import org.springframework.jdbc.core.JdbcTemplate;

class TestClass {
    public void unsafe_jdbc_queryForList_2(String paramName) {
        JdbcTemplate jdbc = new JdbcTemplate();
        // ruleid:jdbc-sql-formatted-string
        List<Map<String, Object>> rows =  jdbc.queryForList("select count(*) from Users where name = '"+paramName+"'");
    }
}
