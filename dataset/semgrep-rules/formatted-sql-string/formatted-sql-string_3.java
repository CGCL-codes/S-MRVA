
package sql.injection;

import java.sql.Connection;
import java.sql.SQLException;
import java.sql.ResultSet;

public class SqlExample {
    public void findAccountsById(String id, String field) throws SQLException {
        String sql = "SELECT ";
        sql += field;
        sql += " FROM accounts WHERE id = '";
        sql += id;
        sql += "'";
        Connection c = DB.getConnection();
        // ruleid:formatted-sql-string
        ResultSet rs = c.createStatement().executeQuery(sql);
    }
}
