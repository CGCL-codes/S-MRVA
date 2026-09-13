
package testcode.sqli;

import io.vertx.sqlclient.SqlClient;
import io.vertx.sqlclient.SqlConnection;

public class VertxSqlClient {
    public void falsePositive1(SqlClient client) {
        String constantValue = "SELECT * FROM test";
        // ok: vertx-sqli
        client.query(constantValue);
    }
}
