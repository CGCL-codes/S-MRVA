
import java.lang.Runtime;
import org.springframework.jdbc.core.JdbcTemplate;

class TestClass {
    public void unsafe_jdbc_update(String paramName, String paramSalary) {
        JdbcTemplate jdbc = new JdbcTemplate();
        // ruleid:jdbc-sql-formatted-string
        String updateQuery = "update Users set salary = '"+paramSalary+"' where name = '"+paramName+"'";
        jdbc.update(updateQuery);
    }
}
