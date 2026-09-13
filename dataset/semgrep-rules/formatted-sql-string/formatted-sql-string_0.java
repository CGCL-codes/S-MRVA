
package sql.injection;

import java.sql.Connection;
import java.sql.SQLException;
import java.sql.ResultSet;

public class SqlExample {
    public void staticQuery() throws SQLException {
        Connection c = DB.getConnection();
        // ok:formatted-sql-string
        ResultSet rs = c.createStatement().executeQuery("SELECT * FROM happy_messages");
    }
}
