
package testcode.sqli;

import io.vertx.sqlclient.SqlClient;
import io.vertx.sqlclient.SqlConnection;

public class VertxSqlClient {
    public void falsePositive2(SqlConnection conn) {
        String constantValue = "SELECT * FROM test";
        // ok: vertx-sqli
        conn.query(constantValue);
    }
}
