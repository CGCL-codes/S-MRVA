
public class Cls {
    public void ldapBind(Environment env) {
        // ruleid:anonymous-ldap-bind
        env.put(Context.SECURITY_AUTHENTICATION, "none");
        DirContext ctx = new InitialDirContext(env);
    }
}
