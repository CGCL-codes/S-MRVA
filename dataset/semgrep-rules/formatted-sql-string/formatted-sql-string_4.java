
package sql.injection;

import java.sql.Connection;
import java.sql.SQLException;
import java.sql.ResultSet;

public class SqlExample2 {
    public void getAllFields(String tableName) throws SQLException {
        Connection c = db.getConnection();
        // ruleid:formatted-sql-string
        ResultSet rs = c.createStatement().execute("SELECT * FROM " + tableName);
    }
}
