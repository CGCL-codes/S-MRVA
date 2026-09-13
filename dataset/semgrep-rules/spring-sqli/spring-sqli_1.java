
package testcode.sqli;

import org.springframework.jdbc.core.PreparedStatementCreatorFactory;
import org.springframework.jdbc.core.SqlParameter;
import org.springframework.dao.DataAccessException;
import org.springframework.jdbc.core.*;
import java.sql.*;
import java.util.ArrayList;

public class SpringPreparedStatementCreatorFactory {
    public void queryUnsafe(String input) {
        String sql = "select * from Users where name = '" + input + "' id=?";
        // ruleid:spring-sqli
        new PreparedStatementCreatorFactory(sql, new int[] {Types.INTEGER});
    }
}
