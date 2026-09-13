
public class Cls {
    public void ldapBindSafe(Environment env) {
        env.put(Context.SECURITY_AUTHENTICATION, "simple");
        DirContext ctx = new InitialDirContext(env);
    }
}
