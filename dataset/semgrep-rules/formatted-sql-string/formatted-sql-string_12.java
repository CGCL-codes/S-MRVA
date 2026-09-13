
package sql.injection;

public class FalsePositiveCase {
    private ApiClient apiClient;

    public void test(String parameter) throws ApiException {
        com.squareup.okhttp.Call call = constructHttpCall(parameter);
        // ok: formatted-sql-string
        apiClient.execute(call);
        // ok: formatted-sql-string
        apiClient.execute(call);
        apiClient.run(call);
    }
}
