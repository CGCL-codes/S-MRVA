
package testcode.sqli;

import io.vertx.sqlclient.SqlClient;
import io.vertx.sqlclient.SqlConnection;

public class VertxSqlClient {
    public void injection3(SqlConnection conn, String injection) {
        // ruleid: vertx-sqli
        conn.prepare(injection);
    }
}
