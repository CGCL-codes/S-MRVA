
package testcode.sqli;

import io.vertx.sqlclient.SqlClient;
import io.vertx.sqlclient.SqlConnection;

public class VertxSqlClient {
    public void injection2(SqlClient client, String injection) {
        // ruleid: vertx-sqli
        client.preparedQuery(injection);
    }
}
