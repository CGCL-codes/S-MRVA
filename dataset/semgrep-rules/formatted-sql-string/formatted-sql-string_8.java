
package sql.injection;

import java.sql.Connection;
import java.sql.SQLException;
import java.sql.ResultSet;

public class SQLExample3 {
    public void findAccountsById(String id) throws SQLException {
        String sql = String.format("SELECT * FROM accounts WHERE id = '%s'", id);
        Connection c = db.getConnection();
        // ruleid:formatted-sql-string
        ResultSet rs = c.createStatement().execute(sql);
    }
}
