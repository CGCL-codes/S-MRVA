
package testcode.ldap;

import com.sun.jndi.ldap.LdapCtx;
import javax.naming.Context;
import javax.naming.InvalidNameException;
import javax.naming.NamingEnumeration;
import javax.naming.NamingException;
import javax.naming.directory.DirContext;
import javax.naming.directory.InitialDirContext;
import javax.naming.directory.SearchControls;
import javax.naming.directory.SearchResult;
import javax.naming.event.EventDirContext;
import javax.naming.ldap.InitialLdapContext;
import javax.naming.ldap.LdapContext;
import javax.naming.ldap.LdapName;
import java.util.Properties;

public class JndiLdapAdditionalSignature {

    // ruleid: ldap-injection
    public void ldapInjectionSunApi6(String input) throws NamingException {
        Properties props = new Properties();
        props.put(Context.INITIAL_CONTEXT_FACTORY, "com.sun.jndi.ldap.LdapCtxFactory");
        props.put(Context.PROVIDER_URL, "ldap://ldap.example.com");
        props.put(Context.REFERRAL, "ignore");

        SearchControls ctrls = new SearchControls();
        ctrls.setReturningAttributes(new String[]{"givenName", "sn"});
        ctrls.setSearchScope(SearchControls.SUBTREE_SCOPE);

        EventDirContext context6 = new InitialDirContext(props);

        NamingEnumeration<SearchResult> answers;
        answers = context6.search("dc=People,dc=example,dc=com", "(uid=" + input + ")", new Object[0], ctrls);
    }
}
