
package sql.injection;

import java.sql.Connection;
import java.sql.PreparedStatement;
import java.sql.ResultSet;
import java.util.concurrent.Callable;

public class SqlExampleNonStringBuilderConstructor{
    public Retry<ResultSet> getRetry(final String mainQuery, final Connection connection) {
        return new Retry<>(
            new Callable<ResultSet>() {
                public ResultSet call() throws SQLException {
                    PreparedStatement statement = connection.prepareStatement(
                        mainQuery, ResultSet.TYPE_FORWARD_ONLY, ResultSet.CONCUR_READ_ONLY);
                    statement.setFetchSize(Integer.MIN_VALUE);
                    // ok: formatted-sql-string
                    return statement.executeQuery ();
                }
            },
            Retry.RETRY_FOREVER);
    }
}
