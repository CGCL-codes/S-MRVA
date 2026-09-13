
package sql.injection;

import java.sql.Statement;

public class tableConcatStatements {
    public void tableConcat() {
        // ok:formatted-sql-string
        stmt.execute("DROP TABLE " + tableName);
        stmt.execute(String.format("CREATE TABLE %s", tableName));
    }
}
