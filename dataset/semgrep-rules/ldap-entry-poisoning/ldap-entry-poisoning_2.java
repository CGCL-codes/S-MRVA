
public class Cls {
    public void ldapSearchSafe(Environment env) {
        DirContext ctx = new InitialDirContext();
        ctx.search(query, filter,
            new SearchControls(scope, countLimit, timeLimit, attributes,
            false, //Disable
            deref));
    }
}
