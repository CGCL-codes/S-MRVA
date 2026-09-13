
package sql.injection;

import java.sql.Connection;
import java.sql.SQLException;
import java.sql.ResultSet;

public class SqlExample {
    public void findAccountsById(String id) throws SQLException {
        String sql = "SELECT * "
            + "FROM accounts WHERE id = '"
            + id
            + "'";
        Connection c = DB.getConnection();
        // ruleid:formatted-sql-string
        ResultSet rs = c.createStatement().executeQuery(sql);
    }
}
