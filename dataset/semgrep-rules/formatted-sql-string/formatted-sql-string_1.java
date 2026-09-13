
package sql.injection;

import java.sql.Connection;
import java.sql.SQLException;
import java.sql.ResultSet;

public class SqlExample {
    public void getAllFields(String tableName) throws SQLException {
        Connection c = DB.getConnection();
        // ruleid:formatted-sql-string
        ResultSet rs = c.createStatement().executeQuery("SELECT * FROM " + tableName);
    }
}
