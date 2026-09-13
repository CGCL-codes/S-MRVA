
package sql.injection;

import java.sql.Connection;
import java.sql.PreparedStatement;
import java.sql.ResultSet;
import javax.servlet.http.HttpServletRequest;

public class SqlExampleFocusMetavar {
    public void get(HttpServletRequest req) {
        Connection c = DB.getConnection();
        String p = req.getParam("param");
        PreparedStatement statement = c.prepareStatment("SELECT * FROM " + p);
        // ruleid: formatted-sql-string
        ResultSet rs = statement.executeQuery();
    }
}
