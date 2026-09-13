
public class Cls {
    public void ldapSearchEntryPoisonViaSetter(Environment env) {
        DirContext ctx = new InitialDirContext();
        // ruleid:ldap-entry-poisoning
        SearchControls ctrls = new SearchControls();
        ctrls.setReturningObjFlag(true);
    }
}
