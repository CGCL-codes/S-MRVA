# Static Rule Testing Report: anonymous-ldap-bind

## Summary

- Language: java
- Rule goal: Detects anonymous LDAP bind via Java JNDI (CWE-287: Improper Authentication; OWASP A02:2017 Broken Authentication / A07:2021 Identification and Authentication Failures). The vulnerable configuration occurs when code sets the JNDI LDAP authentication environment property to the anonymous mode and then constructs an InitialDirContext with that environment. Concretely, the rule matches `$ENV.put($CTX.SECURITY_AUTHENTICATION, "none"); ... $DCTX = new InitialDirContext($ENV, ...);` where `$ENV` is the same environment object (typically a Hashtable/Map, or a method parameter) that is mutated with the key `Context.SECURITY_AUTHENTICATION` (equivalent to the string key `java.naming.security.authentication`) and value literal `"none"`, and then flows into the `InitialDirContext` constructor. In JNDI, `SECURITY_AUTHENTICATION` controls the LDAP bind mode: `"none"` means anonymous/no credentials, `"simple"` means simple bind with credentials, and `"strong"` means SASL. Setting it to `"none"` causes the provider to perform an anonymous LDAP bind, so any unauthenticated attacker with network access to the LDAP server can execute LDAP statements (searches, binds, modifications) under anonymous permissions. The rule is an audit-style syntactic/data-flow match: it requires the `put` on the environment object to precede the `InitialDirContext` construction, allows arbitrary intervening statements via the `...` ellipsis, and allows extra constructor arguments via the trailing `...`. It does not track user input; it detects the insecure authentication configuration itself. Metadata: likelihood LOW, impact HIGH, confidence LOW, severity WARNING.
- Total generated mutants: 31
- Total verified mutants: 31
- Reportable mutants: 13
- False positives: 4
- False negatives: 9

## Original Rule Implementation

```
# File: dataset/semgrep-rules/anonymous-ldap-bind/anonymous-ldap-bind.yaml
rules:
- id: anonymous-ldap-bind
  metadata:
    cwe:
    - 'CWE-287: Improper Authentication'
    owasp:
    - A02:2017 - Broken Authentication
    - A07:2021 - Identification and Authentication Failures
    source-rule-url: https://find-sec-bugs.github.io/bugs.htm#LDAP_ANONYMOUS
    category: security
    technology:
    - java
    references:
    - https://owasp.org/Top10/A07_2021-Identification_and_Authentication_Failures
    cwe2022-top25: true
    cwe2021-top25: true
    subcategory:
    - audit
    likelihood: LOW
    impact: HIGH
    confidence: LOW
  message: >-
    Detected anonymous LDAP bind.
    This permits anonymous users to execute LDAP statements. Consider enforcing
    authentication for LDAP. See https://docs.oracle.com/javase/tutorial/jndi/ldap/auth_mechs.html
    for more information.
  severity: WARNING
  pattern: |
    $ENV.put($CTX.SECURITY_AUTHENTICATION, "none");
    ...
    $DCTX = new InitialDirContext($ENV, ...);
  languages:
  - java


```

## Original Seed Test Case

```java

public class Cls {
    public void ldapBind(Environment env) {
        // ruleid:anonymous-ldap-bind
        env.put(Context.SECURITY_AUTHENTICATION, "none");
        DirContext ctx = new InitialDirContext(env);
    }
}

```

## All Verified Mutants

### 1. P0 · FN · anonymous_authentication_configuration

- Should report: True
- Risk type: false_negative
- Snippet source: 
- Bug description: The code configures JNDI LDAP authentication to anonymous mode using setProperty, causing an anonymous LDAP bind. The static analyzer only detects the put-based variant, so it fails to flag this semantically equivalent insecure authentication configuration.
- Assessment reason: The static analyzer reported 0 findings, but the code sets the JNDI LDAP authentication property to 'none' via env.setProperty(DirContext.SECURITY_AUTHENTICATION, 'none') and then passes that Properties-based environment to new InitialDirContext(env). This is semantically equivalent to the put-based anonymous bind configuration the rule aims to detect, so the analyzer missed a real instance of anonymous LDAP authentication. The pattern is realistic because Properties is a standard JNDI environment and setProperty is a natural API for it. The impact is high because anonymous LDAP bind allows unauthenticated attackers with network access to perform LDAP operations under anonymous permissions. This is therefore a genuine and valuable false negative.
- LLM judge says issue: True
- Tool says issue: False

#### Reproduction Code

```java
import java.util.Properties;
import javax.naming.directory.DirContext;
import javax.naming.directory.InitialDirContext;

class Environment extends Properties {}

public class Cls {
    public void ldapBind(Environment env) {
        // ruleid:anonymous-ldap-bind
        env.setProperty(DirContext.SECURITY_AUTHENTICATION, "none");
        DirContext ctx = new InitialDirContext(env);
    }
}
```

#### Oracle

```json
{
  "has_issue": true,
  "reason": "This mutation aims to remain vulnerable and expose a potential false negative.",
  "expected_focus": "anonymous_authentication_configuration"
}
```

### 2. P0 · FN · anonymous_authentication_configuration

- Should report: True
- Risk type: false_negative
- Snippet source: 
- Bug description: The code sets the JNDI security authentication property to 'none' based on a conditional check, causing an anonymous LDAP bind when the authentication mode is empty or none. This allows unauthenticated users to perform LDAP operations, potentially leading to unauthorized access or data modification.
- Assessment reason: The code conditionally sets Context.SECURITY_AUTHENTICATION to 'none' when the existing mode is empty or none, then constructs an InitialDirContext with that environment. This results in an anonymous LDAP bind. The Semgrep rule requires a literal 'none' argument in the put call, so it misses the ternary expression, producing a false negative. The pattern is realistic because defaulting to anonymous authentication when no mode is specified is a plausible configuration in real JNDI code, and it is critical because anonymous bind can allow unauthenticated LDAP operations.
- LLM judge says issue: True
- Tool says issue: False

#### Reproduction Code

```java
import java.util.Objects;
import javax.naming.Context;
import javax.naming.directory.DirContext;
import javax.naming.directory.InitialDirContext;
import org.apache.cxf.common.util.GenericUtils;
import org.apache.cxf.common.util.PropertyResolverUtils;

public class Cls {
    public void ldapBind(Environment env) {
        // ruleid:anonymous-ldap-bind
        String mode = Objects.toString(env.get(Context.SECURITY_AUTHENTICATION), null);
        boolean anonymous = GenericUtils.isEmpty(mode) || PropertyResolverUtils.isNoneValue(mode);
        env.put(Context.SECURITY_AUTHENTICATION, anonymous ? "none" : mode);
        DirContext ctx = new InitialDirContext(env);
    }
}
```

#### Oracle

```json
{
  "has_issue": true,
  "reason": "This mutation aims to remain vulnerable and expose a potential false negative.",
  "expected_focus": "anonymous_authentication_configuration"
}
```

### 3. P0 · FN · anonymous_authentication_configuration

- Should report: True
- Risk type: false_negative
- Snippet source: 
- Bug description: The JNDI environment is configured with Context.SECURITY_AUTHENTICATION="none" and then used to create an InitialDirContext, causing an anonymous LDAP bind with no credentials. This disables authentication for the LDAP connection and can allow unauthenticated access to directory operations; the static analyzer failed to report this vulnerable configuration.
- Assessment reason: The code sets Context.SECURITY_AUTHENTICATION to "none" on the same environment object that is then passed to new InitialDirContext(env). This is exactly the anonymous JNDI/LDAP bind configuration the rule is designed to detect. The switch-case wrapper is a realistic control-flow variation (an authMethod branch) and does not change the semantics: authMethod is NONE, so the put executes before the context is constructed. Semgrep returned 0 findings, so this is a genuine false negative, not an artifact. Anonymous LDAP bind can let unauthenticated network attackers query or modify directory data depending on server ACLs, so it is security-relevant.
- LLM judge says issue: True
- Tool says issue: False

#### Reproduction Code

```java
import javax.naming.Context;
import javax.naming.directory.DirContext;
import javax.naming.directory.InitialDirContext;

public class Cls {
    public void ldapBind(Environment env) {
        // ruleid:anonymous-ldap-bind
        final int NONE = 0;
        int authMethod = NONE;
        switch (authMethod) {
            case NONE:
                env.put(Context.SECURITY_AUTHENTICATION, "none");
                break;
            default:
                break;
        }
        DirContext ctx = new InitialDirContext(env);
    }
}
```

#### Oracle

```json
{
  "has_issue": true,
  "reason": "This mutation aims to remain vulnerable and expose a potential false negative.",
  "expected_focus": "anonymous_authentication_configuration"
}
```

### 4. P2 · FN · anonymous_authentication_configuration

- Should report: False
- Risk type: false_negative
- Snippet source: 
- Bug description: 
- Assessment reason: 
- LLM judge says issue: True
- Tool says issue: False

#### Reproduction Code

```java
import javax.naming.Context;
import javax.naming.InitialDirContext;
import javax.naming.directory.DirContext;

public class Cls {
    public void ldapBind(Environment env) {
        // ruleid:anonymous-ldap-bind
        env.put(switch (Environment.CLUSTER_SECURITY_AUTHENTICATION) {
            case NONE -> "java.naming.security.authentication";
            default -> Context.SECURITY_AUTHENTICATION;
        }, "none");
        DirContext ctx = new InitialDirContext(env);
    }
}
```

#### Oracle

```json
{
  "has_issue": true,
  "reason": "This mutation aims to remain vulnerable and expose a potential false negative.",
  "expected_focus": "anonymous_authentication_configuration"
}
```

### 5. P0 · FN · anonymous_authentication_configuration

- Should report: True
- Risk type: false_negative
- Snippet source: 
- Bug description: The code configures JNDI LDAP authentication to anonymous mode by putting "java.naming.security.authentication" = "none" into the environment and then creating an InitialDirContext, causing an anonymous LDAP bind with no credentials. The static analyzer fails to detect this because the property key is hidden behind a named constant.
- Assessment reason: The static analyzer reports zero findings, but the code genuinely sets the JNDI LDAP authentication property to the literal anonymous mode "none" and then constructs an InitialDirContext with the same environment. The analyzer misses it because the key is referenced through the constant HADOOP_SECURITY_AUTHENTICATION instead of the Context.SECURITY_AUTHENTICATION expression. This is a realistic evasion pattern: real codebases often define constants for property names, and the underlying insecure configuration is exactly what the rule targets. The impact is high because anonymous LDAP bind allows unauthenticated access to LDAP operations. Therefore this is a valuable false negative.
- LLM judge says issue: True
- Tool says issue: False

#### Reproduction Code

```java
import java.util.Hashtable;
import javax.naming.InitialDirContext;
import javax.naming.directory.DirContext;

class Environment extends Hashtable<String, Object> {}

public class Cls {
    private static final String HADOOP_SECURITY_AUTHENTICATION = "java.naming.security.authentication";

    public void ldapBind(Environment env) {
        // ruleid:anonymous-ldap-bind
        env.put(HADOOP_SECURITY_AUTHENTICATION, "none");
        DirContext ctx = new InitialDirContext(env);
    }
}
```

#### Oracle

```json
{
  "has_issue": true,
  "reason": "This mutation aims to remain vulnerable and expose a potential false negative.",
  "expected_focus": "anonymous_authentication_configuration"
}
```

### 6. P1 · FP · anonymous_authentication_configuration

- Should report: True
- Risk type: false_positive
- Snippet source: 
- Bug description: The analyzer reports an anonymous LDAP bind, but the code sets `SECURITY_AUTHENTICATION` to `"none"` and then immediately overwrites it with `"GSSAPI"` before creating the initial context, so the final configuration is authenticated. This is a false positive caused by the analyzer not modeling the final value of the mutable environment map.
- Assessment reason: The analyzer flags a potential anonymous LDAP bind based on the earlier `env.put(Context.SECURITY_AUTHENTICATION, "none")` call. However, the code subsequently overwrites the same key with the value of `authentication` ("GSSAPI") before constructing the `InitialDirContext`. Since the final value of the security authentication property is "GSSAPI", the bound context will not perform an anonymous bind. This is a genuine false positive: the analyzer's pattern ignores later overwrites of the same environment key. The pattern of setting a default value and then overriding it is realistic in real codebases. The false positive itself is not a critical security vulnerability.
- LLM judge says issue: False
- Tool says issue: True

#### Reproduction Code

```java
import javax.naming.Context;
import javax.naming.directory.DirContext;
import javax.naming.directory.InitialDirContext;

public class Cls {
    public void ldapBind(Environment env) {
        // ruleid:anonymous-ldap-bind
        String authentication = "GSSAPI";
        env.put(Context.SECURITY_AUTHENTICATION, "none");
        env.put(Context.SECURITY_AUTHENTICATION, authentication);
        DirContext ctx = new InitialDirContext(env);
    }
}
```

#### Oracle

```json
{
  "has_issue": false,
  "reason": "This mutation aims to be a secure variant and expose a potential false positive.",
  "expected_focus": "anonymous_authentication_configuration"
}
```

### 7. P2 · FP · anonymous_authentication_configuration

- Should report: False
- Risk type: false_positive
- Snippet source: 
- Bug description: 
- Assessment reason: 
- LLM judge says issue: False
- Tool says issue: True

#### Reproduction Code

```java
import javax.naming.Context;
import javax.naming.directory.DirContext;
import javax.naming.directory.InitialDirContext;

public class Cls {
    public void ldapBind(Environment env) {
        // ruleid:anonymous-ldap-bind
        env.put(Context.SECURITY_AUTHENTICATION, "none");
        // Default authentication would be anonymous and this is used if nothing is specified for
        // the SECURITY_AUTHENTICATION field.
        env.put(Context.SECURITY_AUTHENTICATION, "simple");
        DirContext ctx = new InitialDirContext(env);
    }
}
```

#### Oracle

```json
{
  "has_issue": false,
  "reason": "This mutation aims to be a secure variant and expose a potential false positive.",
  "expected_focus": "anonymous_authentication_configuration"
}
```

### 8. P2 · NONE · anonymous_authentication_configuration

- Should report: False
- Risk type: false_positive
- Snippet source: 
- Bug description: 
- Assessment reason: 
- LLM judge says issue: False
- Tool says issue: False

#### Reproduction Code

```java
import javax.naming.directory.DirContext;
import javax.naming.directory.InitialDirContext;

public class Cls {
    public static final String AUTH_IMPL_ADS_SECURITY_AUTHENTICATION = "auth.impl.ads.security.authentication";

    public void ldapBind(Environment env) {
        // ruleid:anonymous-ldap-bind
        env.put(AUTH_IMPL_ADS_SECURITY_AUTHENTICATION, "none");
        DirContext ctx = new InitialDirContext(env);
    }
}
```

#### Oracle

```json
{
  "has_issue": false,
  "reason": "This mutation aims to be a secure variant and expose a potential false positive.",
  "expected_focus": "anonymous_authentication_configuration"
}
```

### 9. P2 · NONE · anonymous_authentication_configuration

- Should report: False
- Risk type: false_positive
- Snippet source: 
- Bug description: 
- Assessment reason: 
- LLM judge says issue: False
- Tool says issue: False

#### Reproduction Code

```java
import javax.naming.Context;
import javax.naming.directory.DirContext;
import javax.naming.directory.InitialDirContext;

public class Cls {
    public void ldapBind(Environment env) {
        // ruleid:anonymous-ldap-bind
        env.put(Context.SECURITY_AUTHENTICATION, "simple");
        DirContext ctx = new InitialDirContext(env);
    }
}
```

#### Oracle

```json
{
  "has_issue": false,
  "reason": "This mutation aims to be a secure variant and expose a potential false positive.",
  "expected_focus": "anonymous_authentication_configuration"
}
```

### 10. P0 · FN · anonymous_authentication_configuration

- Should report: True
- Risk type: false_positive
- Snippet source: 
- Bug description: Setting JNDI SECURITY_AUTHENTICATION to "none" when credentials are missing configures an anonymous LDAP bind, which can permit unauthenticated attackers to perform LDAP operations under anonymous permissions.
- Assessment reason: The code conditionally sets Context.SECURITY_AUTHENTICATION to "none" when SECURITY_CREDENTIALS is absent, and then constructs an InitialDirContext with the same environment, which results in an anonymous LDAP bind in that path. This matches the rule's intent of detecting anonymous authentication configuration. The static analyzer produced 0 findings, likely because the put is nested inside an if block and the rule's pattern expected the put and the InitialDirContext construction at the same syntactic level. This is a genuine false negative: the insecure configuration is present and flows into the context construction. The pattern is realistic (conditional fallback to anonymous bind) and the impact is high because anonymous LDAP bind can allow unauthenticated access.
- LLM judge says issue: True
- Tool says issue: False

#### Reproduction Code

```java
import javax.naming.Context;
import javax.naming.directory.DirContext;
import javax.naming.directory.InitialDirContext;
import java.util.Hashtable;

public class Cls {
    public void ldapBind(Environment env) {
        // ruleid:anonymous-ldap-bind
        Object[] keys = {
            Context.REFERRAL,
            Context.SECURITY_AUTHENTICATION,
            Context.SECURITY_CREDENTIALS
        };
        if (env.get(keys[2]) == null) {
            env.put(Context.SECURITY_AUTHENTICATION, "none");
        }
        DirContext ctx = new InitialDirContext(env);
    }
}

class Environment extends Hashtable<String, Object> {
}
```

#### Oracle

```json
{
  "has_issue": false,
  "reason": "This mutation aims to be a secure variant and expose a potential false positive.",
  "expected_focus": "anonymous_authentication_configuration"
}
```

### 11. P2 · NONE · environment_object_flow_and_ordering

- Should report: False
- Risk type: false_negative
- Snippet source: 
- Bug description: 
- Assessment reason: 
- LLM judge says issue: False
- Tool says issue: False

#### Reproduction Code

```java
import java.util.Hashtable;
import javax.naming.directory.DirContext;
import javax.naming.directory.InitialDirContext;

class Environment extends Hashtable<String, String> {
}

public class Cls {
    public void ldapBind(Environment env) {
        // ruleid:anonymous-ldap-bind
        DirContext ctx = new InitialDirContext(env);
    }
}
```

#### Oracle

```json
{
  "has_issue": true,
  "reason": "This mutation aims to remain vulnerable and expose a potential false negative.",
  "expected_focus": "environment_object_flow_and_ordering"
}
```

### 12. P2 · FN · environment_object_flow_and_ordering

- Should report: False
- Risk type: false_negative
- Snippet source: 
- Bug description: 
- Assessment reason: 
- LLM judge says issue: True
- Tool says issue: False

#### Reproduction Code

```java
import java.util.Hashtable;
import java.util.Objects;
import javax.naming.Context;
import javax.naming.NamingException;
import javax.naming.directory.DirContext;
import javax.naming.directory.InitialDirContext;

public class Cls {
    public void ldapBind(Environment env) {
        // ruleid:anonymous-ldap-bind
        String mode = Objects.toString(env.get(Context.SECURITY_AUTHENTICATION), null);
        boolean anonymous = GenericUtils.isEmpty(mode) || PropertyResolverUtils.isNoneValue(mode);
        env.put(Context.SECURITY_AUTHENTICATION, anonymous ? "n" + "one" : mode);
        DirContext ctx;
        try {
            ctx = new InitialDirContext(env);
        } catch (NamingException e) {
            throw new RuntimeException(e);
        }
    }
}

class Environment extends Hashtable<String, Object> {
}

class GenericUtils {
    public static boolean isEmpty(String s) {
        return s == null || s.isEmpty();
    }
}

class PropertyResolverUtils {
    public static boolean isNoneValue(String s) {
        return "none".equalsIgnoreCase(s);
    }
}
```

#### Oracle

```json
{
  "has_issue": true,
  "reason": "This mutation aims to remain vulnerable and expose a potential false negative.",
  "expected_focus": "environment_object_flow_and_ordering"
}
```

### 13. P0 · FN · environment_object_flow_and_ordering

- Should report: True
- Risk type: false_negative
- Snippet source: 
- Bug description: The environment property Context.SECURITY_AUTHENTICATION is set to "none", causing JNDI/LDAP to perform an anonymous bind with no credentials. This allows any unauthenticated attacker with network access to execute LDAP operations under anonymous permissions, leading to improper authentication.
- Assessment reason: The code sets Context.SECURITY_AUTHENTICATION to "none" through the authType variable and then passes the same environment object to new InitialDirContext(env), which produces an anonymous LDAP bind. The Semgrep rule specifically looks for the literal string "none" in the put call, so it misses this semantically equivalent indirect assignment. This is a genuine false negative because the analyzer was designed to detect this insecure authentication configuration but failed due to its syntactic matching limitation. Using a variable or configuration-derived value for the authentication type is a realistic pattern in real codebases, and anonymous LDAP bind has high security impact because it allows unauthenticated access to the LDAP server.
- LLM judge says issue: True
- Tool says issue: False

#### Reproduction Code

```java
import javax.naming.Context;
import javax.naming.directory.DirContext;
import javax.naming.directory.InitialDirContext;

public class Cls {
    public void ldapBind(Environment env) {
        // ruleid:anonymous-ldap-bind
        String authType = "none";
        if (authType != null) {
            env.put(Context.SECURITY_AUTHENTICATION, authType);
        }
        DirContext ctx = new InitialDirContext(env);
    }
}
```

#### Oracle

```json
{
  "has_issue": true,
  "reason": "This mutation aims to remain vulnerable and expose a potential false negative.",
  "expected_focus": "environment_object_flow_and_ordering"
}
```

### 14. P0 · FN · environment_object_flow_and_ordering

- Should report: True
- Risk type: false_negative
- Snippet source: 
- Bug description: The code disables LDAP authentication by setting the JNDI property java.naming.security.authentication to "none" on the environment object and constructing an InitialDirContext from it, causing an anonymous LDAP bind. Any unauthenticated attacker with network access to the LDAP server can then perform LDAP operations under anonymous permissions. The static analyzer fails to detect this because it only matches the literal put(Context.SECURITY_AUTHENTICATION, "none") form and does not follow the setProperty-with-variable equivalent.
- Assessment reason: The analyzer produced 0 findings, yet the code genuinely configures an anonymous LDAP bind: it sets the JNDI property java.naming.security.authentication to "none" (via setProperty with a variable initialized to that literal) on the environment object and then passes that same environment into new InitialDirContext(...). In JNDI, this value forces the provider to perform an anonymous/no-credential LDAP bind, which is exactly the insecure authentication configuration the rule targets. The analyzer missed it only because the mutation avoided the specific put(Context.SECURITY_AUTHENTICATION, "none") + literal syntactic pattern the rule matches, so this is a genuine false negative that is grounded in the shown code. The pattern of setting JNDI/LDAP security properties programmatically is a realistic, real-world configuration approach (not contrived), and anonymous LDAP bind has high security impact (CWE-287 / A07:2021, metadata impact HIGH), making it both common and critical.
- LLM judge says issue: True
- Tool says issue: False

#### Reproduction Code

```java
import javax.naming.directory.DirContext;
import javax.naming.directory.InitialDirContext;
import java.util.Hashtable;
import java.util.Properties;

public class Cls {
    public void ldapBind(Environment env) {
        // ruleid:anonymous-ldap-bind
        String SEARCH_SECURITY_LEVEL = "none";
        env.setProperty("java.naming.security.authentication", SEARCH_SECURITY_LEVEL);
        DirContext ctx = new InitialDirContext((Hashtable)env);
    }
}

class Environment extends Properties {
}
```

#### Oracle

```json
{
  "has_issue": true,
  "reason": "This mutation aims to remain vulnerable and expose a potential false negative.",
  "expected_focus": "environment_object_flow_and_ordering"
}
```

### 15. P0 · FN · environment_object_flow_and_ordering

- Should report: True
- Risk type: false_negative
- Snippet source: 
- Bug description: The JNDI environment is configured with SECURITY_AUTHENTICATION="none" before creating an InitialDirContext, causing the LDAP provider to perform an anonymous bind with no credentials. This allows unauthenticated access to the LDAP server and can permit unauthorized searches, binds, or modifications under anonymous permissions.
- Assessment reason: The code sets Context.SECURITY_AUTHENTICATION to "none" on the env object and later passes that same env object to the InitialDirContext constructor. Although the put is inside an if block, the condition is a constant true, so the anonymous authentication configuration executes before the context is created. The analyzer's sequence-based pattern misses this control-flow variation, but the insecure anonymous LDAP bind is genuinely present. Conditional configuration of authentication is a realistic pattern, and anonymous LDAP bind is a high-impact authentication weakness, so this is a valuable false negative.
- LLM judge says issue: True
- Tool says issue: False

#### Reproduction Code

```java
import javax.naming.Context;
import javax.naming.directory.DirContext;
import javax.naming.directory.InitialDirContext;

public class Cls {
    public void ldapBind(Environment env) {
        // ruleid:anonymous-ldap-bind
        boolean anonymousAuthentication = true;
        if (anonymousAuthentication) {
            env.put(Context.SECURITY_AUTHENTICATION, "none");
        }
        DirContext ctx = new InitialDirContext(env);
    }
}
```

#### Oracle

```json
{
  "has_issue": true,
  "reason": "This mutation aims to remain vulnerable and expose a potential false negative.",
  "expected_focus": "environment_object_flow_and_ordering"
}
```

### 16. P2 · NONE · environment_object_flow_and_ordering

- Should report: False
- Risk type: false_negative
- Snippet source: 
- Bug description: 
- Assessment reason: 
- LLM judge says issue: False
- Tool says issue: False

#### Reproduction Code

```java
import javax.naming.Context;
import javax.naming.directory.InitialDirContext;
import javax.naming.directory.DirContext;

public class Cls {
    public void ldapBind(Environment env) {
        // ruleid:anonymous-ldap-bind
        String _ldapHost = "localhost";
        String _ldapPort = "389";
        env.put(Context.PROVIDER_URL, String.format("ldaps://%s:%s", _ldapHost, _ldapPort));
        env.put(Context.SECURITY_PROTOCOL, "ssl");
        DirContext ctx = new InitialDirContext(env);
    }
}
```

#### Oracle

```json
{
  "has_issue": true,
  "reason": "This mutation aims to remain vulnerable and expose a potential false negative.",
  "expected_focus": "environment_object_flow_and_ordering"
}
```

### 17. P2 · FP · environment_object_flow_and_ordering

- Should report: False
- Risk type: false_positive
- Snippet source: 
- Bug description: 
- Assessment reason: 
- LLM judge says issue: False
- Tool says issue: True

#### Reproduction Code

```java
import javax.naming.Context;
import javax.naming.directory.DirContext;
import javax.naming.directory.InitialDirContext;

public class Cls {
    public void ldapBind(Environment env) {
        // ruleid:anonymous-ldap-bind
        env.put(Context.SECURITY_AUTHENTICATION, "none");
        DirContext ctx = null;
        if (ctx == null) {
            env.put(Context.SECURITY_AUTHENTICATION, "simple");
            ctx = new InitialDirContext(env);
        }
    }
}
```

#### Oracle

```json
{
  "has_issue": false,
  "reason": "This mutation aims to be a secure variant and expose a potential false positive.",
  "expected_focus": "environment_object_flow_and_ordering"
}
```

### 18. P2 · FP · environment_object_flow_and_ordering

- Should report: False
- Risk type: false_positive
- Snippet source: 
- Bug description: 
- Assessment reason: 
- LLM judge says issue: False
- Tool says issue: True

#### Reproduction Code

```java
import javax.naming.Context;
import javax.naming.directory.InitialDirContext;
import javax.naming.directory.DirContext;

public class Cls {
    public void ldapBind(Environment env) {
        // ruleid:anonymous-ldap-bind
        env.put(Context.SECURITY_AUTHENTICATION, "none");
        String key = Context.SECURITY_AUTHENTICATION;
        String value = "simple";
        env.put(key, value);
        DirContext ctx = new InitialDirContext(env);
    }
}
```

#### Oracle

```json
{
  "has_issue": false,
  "reason": "This mutation aims to be a secure variant and expose a potential false positive.",
  "expected_focus": "environment_object_flow_and_ordering"
}
```

### 19. P2 · FP · environment_object_flow_and_ordering

- Should report: False
- Risk type: false_positive
- Snippet source: 
- Bug description: 
- Assessment reason: 
- LLM judge says issue: False
- Tool says issue: True

#### Reproduction Code

```java
import javax.naming.Context;
import javax.naming.directory.InitialDirContext;
import javax.naming.directory.DirContext;

public class Cls {
    public void ldapBind(Environment env) {
        // ruleid:anonymous-ldap-bind
        env.put(Context.SECURITY_AUTHENTICATION, "none");
        env.put(Context.SECURITY_AUTHENTICATION, "simple");
        DirContext ctx = new InitialDirContext(env);
    }
}
```

#### Oracle

```json
{
  "has_issue": false,
  "reason": "This mutation aims to be a secure variant and expose a potential false positive.",
  "expected_focus": "environment_object_flow_and_ordering"
}
```

### 20. P1 · FP · environment_object_flow_and_ordering

- Should report: True
- Risk type: false_positive
- Snippet source: 
- Bug description: The static analyzer incorrectly reports an anonymous LDAP bind because it detects the initial put of SECURITY_AUTHENTICATION to "none" but fails to account for the subsequent put of "simple" that overwrites it before InitialDirContext is constructed. The final configuration uses a simple authenticated bind, so no anonymous bind occurs.
- Assessment reason: The code sets Context.SECURITY_AUTHENTICATION to "none" and then immediately overwrites it with "simple" before constructing InitialDirContext. Because Java Hashtable/Map put replaces the previous value for the same key, the environment passed to InitialDirContext has SECURITY_AUTHENTICATION set to "simple", so the actual bind mode is authenticated and not anonymous. The Semgrep rule matches the earlier "none" put and ignores the later override, producing a false positive. This is a genuine analyzer limitation (lack of last-write tracking), and the pattern of overriding a configuration property is realistic in real codebases. However, the code is secure, so the false positive does not represent a real security vulnerability or significant security problem.
- LLM judge says issue: False
- Tool says issue: True

#### Reproduction Code

```java
import javax.naming.Context;
import javax.naming.directory.DirContext;
import javax.naming.directory.InitialDirContext;

public class Cls {
    public void ldapBind(Environment env) {
        // ruleid:anonymous-ldap-bind
        env.put(Context.SECURITY_AUTHENTICATION, "none");
        env.put(Context.SECURITY_AUTHENTICATION, "simple");
        DirContext ctx = new InitialDirContext(env);
    }
}
```

#### Oracle

```json
{
  "has_issue": false,
  "reason": "This mutation aims to be a secure variant and expose a potential false positive.",
  "expected_focus": "environment_object_flow_and_ordering"
}
```

### 21. P1 · FP · environment_object_flow_and_ordering

- Should report: True
- Risk type: false_positive
- Snippet source: 
- Bug description: The Semgrep rule anonymous-ldap-bind flags the pattern env.put(Context.SECURITY_AUTHENTICATION, "none") followed by new InitialDirContext(env). However, the rule is purely syntactic and does not model that the same key is subsequently overwritten. The code sets SECURITY_AUTHENTICATION to "none" and then immediately sets it again to "GSSAPI" on the same environment object before constructing the InitialDirContext. Since Hashtable.put replaces the prior value, the context is created with "GSSAPI" (SASL/Kerberos) authentication, not anonymous. Thus no anonymous LDAP bind happens and the analyzer's reported issue does not exist at runtime; this is a false positive caused by the rule's lack of overwrite/data-flow tracking.
- Assessment reason: This is a genuine false positive of the analyzer. The rule anonymous-ldap-bind is an audit-style syntactic/data-flow match: it only requires that env.put(Context.SECURITY_AUTHENTICATION, "none") textually precede a new InitialDirContext(env) construction. It does not track stores/overwrites on the same key. In the code, the very next statements overwrite the same key on the same Hashtable-based environment object with the variable authentication = "GSSAPI". Because Hashtable.put replaces the previous value, by the time InitialDirContext(env) is executed the property is "GSSAPI" (SASL/Kerberos), not "none", so no anonymous LDAP bind ever occurs. The LLM judge's diagnosis (the 'none' is immediately overwritten before the context is built) is correct, and the analyzer's blocking finding is therefore a real false negative of overwrite-awareness / a real false positive on secure code. It is valid because the code concretely demonstrates the analyzer's limitation. It is common: reusing a shared environment/config object and re-setting (default-then-override) properties before building the context is a realistic pattern in JNDI/LDAP code. It is not critical: the code as written is actually secure, so this false positive causes analyzer noise/alert fatigue rather than any real authentication or security vulnerability in practice.
- LLM judge says issue: False
- Tool says issue: True

#### Reproduction Code

```java
import java.util.Hashtable;
import javax.naming.Context;
import javax.naming.directory.DirContext;
import javax.naming.directory.InitialDirContext;
import javax.naming.NamingException;

public class Cls {
    public void ldapBind(Environment env) {
        // ruleid:anonymous-ldap-bind
        env.put(Context.SECURITY_AUTHENTICATION, "none");
        String authentication = "GSSAPI";
        env.put(Context.SECURITY_AUTHENTICATION, authentication);
        if ("GSSAPI".equals(authentication)) {
            kerberosOpen(env);
        }
        try {
            DirContext ctx = new InitialDirContext(env);
        } catch (NamingException e) {
            // handle exception
        }
    }

    private void kerberosOpen(Environment env) {
        // stub for Kerberos authentication
    }
}

class Environment extends Hashtable<String, Object> {
}
```

#### Oracle

```json
{
  "has_issue": false,
  "reason": "This mutation aims to be a secure variant and expose a potential false positive.",
  "expected_focus": "environment_object_flow_and_ordering"
}
```

### 22. P0 · FN · initial_dir_context_creation

- Should report: True
- Risk type: false_negative
- Snippet source: 
- Bug description: The environment object is configured with Context.SECURITY_AUTHENTICATION = "none" and then passed to `new InitialDirContext(...)`, causing the LDAP provider to perform an anonymous bind (CWE-287). Because the constructed context is immediately chained with `.getAttributes("")` instead of being assigned to a variable, the Semgrep rule's assignment-based pattern fails to match and the anonymous-bind vulnerability goes undetected (false negative).
- Assessment reason: The rule is designed to catch exactly this insecure JNDI configuration: env.put(Context.SECURITY_AUTHENTICATION, "none") followed by construction of an InitialDirContext with that same environment object, which triggers an anonymous LDAP bind (CWE-287). In the shown code the mutation merely replaced `byte[] val = ...; new InitialDirContext(env)` style assignment with an inline chained call `new InitialDirContext((Hashtable<String,String>)env).getAttributes("").get(...)`. The anonymous-bind configuration is fully preserved, yet Semgrep returned 0 findings because its pattern relies on the constructor being the direct RHS of an assignment. This is a genuine false negative caused by the rule being brittle to method chaining on the constructor result, not a case where the code is actually safe. Method-chaining the freshly constructed context into getAttributes is a realistic coding style, so the evasion is not contrived, and anonymous LDAP bind is a HIGH-impact authentication failure, making the miss security-relevant.
- LLM judge says issue: True
- Tool says issue: False

#### Reproduction Code

```java
import java.util.Hashtable;
import javax.naming.Context;
import javax.naming.directory.InitialDirContext;

public class Cls {
    public void ldapBind(Environment env) {
        // ruleid:anonymous-ldap-bind
        env.put(Context.SECURITY_AUTHENTICATION, "none");
        byte[] val = (byte[]) new InitialDirContext((Hashtable<String, String>)env).getAttributes("").get("certificateRevocationList;binary").get();
    }
}

class Environment extends Hashtable<String, String> {}
```

#### Oracle

```json
{
  "has_issue": true,
  "reason": "This mutation aims to remain vulnerable and expose a potential false negative.",
  "expected_focus": "initial_dir_context_creation"
}
```

### 23. P2 · FN · initial_dir_context_creation

- Should report: False
- Risk type: false_negative
- Snippet source: 
- Bug description: 
- Assessment reason: 
- LLM judge says issue: True
- Tool says issue: False

#### Reproduction Code

```java
import java.util.Hashtable;
import javax.naming.Context;
import javax.naming.directory.DirContext;
import javax.naming.directory.InitialDirContext;

public class Cls {
    public void ldapBind(Environment env) {
        // ruleid:anonymous-ldap-bind
        env.put(Context.SECURITY_AUTHENTICATION, "none");
        DirContext ctx;
        if (env.isEmpty()) {
            ctx = new InitialDirContext();
        } else {
            ctx = new InitialDirContext(new Hashtable<>(env));
        }
    }
}
```

#### Oracle

```json
{
  "has_issue": true,
  "reason": "This mutation aims to remain vulnerable and expose a potential false negative.",
  "expected_focus": "initial_dir_context_creation"
}
```

### 24. P2 · NONE · initial_dir_context_creation

- Should report: False
- Risk type: false_negative
- Snippet source: 
- Bug description: 
- Assessment reason: 
- LLM judge says issue: False
- Tool says issue: False

#### Reproduction Code

```java
import javax.naming.Context;
import javax.naming.directory.DirContext;
import javax.naming.directory.InitialDirContext;

public class Cls {
    public void ldapBind(Environment env) {
        // ruleid:anonymous-ldap-bind
        env.put(Context.SECURITY_AUTHENTICATION, "none");
        DirContext ctx = new InitialDirContext();
        ctx.addToEnvironment(Context.SECURITY_AUTHENTICATION, "none");
    }
}
```

#### Oracle

```json
{
  "has_issue": true,
  "reason": "This mutation aims to remain vulnerable and expose a potential false negative.",
  "expected_focus": "initial_dir_context_creation"
}
```

### 25. P2 · NONE · initial_dir_context_creation

- Should report: False
- Risk type: false_negative
- Snippet source: 
- Bug description: 
- Assessment reason: 
- LLM judge says issue: True
- Tool says issue: True

#### Reproduction Code

```java
public class Cls {
    public void ldapBind(Environment env) {
        // ruleid:anonymous-ldap-bind
        env.put(Context.SECURITY_AUTHENTICATION, "none");
        DirContext ctx = new InitialDirContext((Hashtable)env);
    }
}
```

#### Oracle

```json
{
  "has_issue": true,
  "reason": "This mutation aims to remain vulnerable and expose a potential false negative.",
  "expected_focus": "initial_dir_context_creation"
}
```

### 26. P2 · NONE · initial_dir_context_creation

- Should report: False
- Risk type: false_negative
- Snippet source: 
- Bug description: 
- Assessment reason: 
- LLM judge says issue: False
- Tool says issue: False

#### Reproduction Code

```java
import javax.naming.Context;
import javax.naming.directory.DirContext;
import javax.naming.directory.InitialDirContext;

public class Cls {
    public void ldapBind(Environment env) {
        // ruleid:anonymous-ldap-bind
        env.put(Context.SECURITY_AUTHENTICATION, "none");
        DirContext ctx = new InitialDirContext();
    }
}
```

#### Oracle

```json
{
  "has_issue": true,
  "reason": "This mutation aims to remain vulnerable and expose a potential false negative.",
  "expected_focus": "initial_dir_context_creation"
}
```

### 27. P2 · FP · initial_dir_context_creation

- Should report: False
- Risk type: false_positive
- Snippet source: 
- Bug description: 
- Assessment reason: 
- LLM judge says issue: False
- Tool says issue: True

#### Reproduction Code

```java
import java.util.Hashtable;
import javax.naming.Context;
import javax.naming.directory.DirContext;
import javax.naming.directory.InitialDirContext;

public class Cls {
    public void ldapBind(Environment env) {
        // ruleid:anonymous-ldap-bind
        env.put(Context.SECURITY_AUTHENTICATION, "none");
        env = new Hashtable();
        DirContext ctx = new InitialDirContext(env);
    }
}
```

#### Oracle

```json
{
  "has_issue": false,
  "reason": "This mutation aims to be a secure variant and expose a potential false positive.",
  "expected_focus": "initial_dir_context_creation"
}
```

### 28. P2 · NONE · initial_dir_context_creation

- Should report: False
- Risk type: false_positive
- Snippet source: 
- Bug description: 
- Assessment reason: 
- LLM judge says issue: True
- Tool says issue: True

#### Reproduction Code

```java
import javax.naming.Context;
import javax.naming.NamingException;
import javax.naming.directory.DirContext;
import javax.naming.directory.InitialDirContext;

public class Cls {
    public void ldapBind(Environment env) {
        // ruleid:anonymous-ldap-bind
        env.put(Context.SECURITY_AUTHENTICATION, "none");
        DirContext ctx;
        try {
            ctx = new InitialDirContext(env);
        } catch (NamingException ne) {
            throw new RuntimeException("Cannot connect to LDAP ...");
        }
    }
}
```

#### Oracle

```json
{
  "has_issue": false,
  "reason": "This mutation aims to be a secure variant and expose a potential false positive.",
  "expected_focus": "initial_dir_context_creation"
}
```

### 29. P2 · NONE · initial_dir_context_creation

- Should report: False
- Risk type: false_positive
- Snippet source: 
- Bug description: 
- Assessment reason: 
- LLM judge says issue: True
- Tool says issue: True

#### Reproduction Code

```java
import javax.naming.Context;
import javax.naming.directory.DirContext;
import javax.naming.directory.InitialDirContext;

public class Cls {
    public void ldapBind(Environment env) {
        // ruleid:anonymous-ldap-bind
        env.put(Context.SECURITY_AUTHENTICATION, "none");
        String password = (String) env.get(Context.SECURITY_CREDENTIALS);
        if (password == null || password.isEmpty()) {
            throw new IllegalArgumentException("Anonymous bind not allowed");
        }
        DirContext ctx = new InitialDirContext(env);
    }
}
```

#### Oracle

```json
{
  "has_issue": false,
  "reason": "This mutation aims to be a secure variant and expose a potential false positive.",
  "expected_focus": "initial_dir_context_creation"
}
```

### 30. P2 · FP · initial_dir_context_creation

- Should report: False
- Risk type: false_positive
- Snippet source: 
- Bug description: 
- Assessment reason: 
- LLM judge says issue: False
- Tool says issue: True

#### Reproduction Code

```java
import javax.naming.Context;
import javax.naming.directory.DirContext;
import javax.naming.directory.InitialDirContext;

public class Cls {
    public void ldapBind(Environment env) {
        // ruleid:anonymous-ldap-bind
        env.put(Context.SECURITY_AUTHENTICATION, "none");
        if (env.isEmpty()) {
            DirContext ctx = new InitialDirContext();
        } else {
            env.remove(Context.SECURITY_AUTHENTICATION);
            DirContext ctx = new InitialDirContext(env);
        }
    }
}
```

#### Oracle

```json
{
  "has_issue": false,
  "reason": "This mutation aims to be a secure variant and expose a potential false positive.",
  "expected_focus": "initial_dir_context_creation"
}
```

### 31. P1 · FP · initial_dir_context_creation

- Should report: True
- Risk type: false_positive
- Snippet source: 
- Bug description: The Semgrep rule flags an anonymous LDAP bind based on an earlier `put` of `SECURITY_AUTHENTICATION` to `"none"`, but the same environment key is overwritten with `"simple"` before the `InitialDirContext` is constructed. The final environment value is `"simple"`, so no anonymous bind occurs; the finding is a false positive caused by the rule not tracking overwrites of the environment property.
- Assessment reason: The analyzer reports an anonymous LDAP bind because it matches the earlier `env.put(Context.SECURITY_AUTHENTICATION, "none")` and does not account for the subsequent `env.put(Context.SECURITY_AUTHENTICATION, "simple")` that overwrites the same key before the `InitialDirContext` is constructed. Since JNDI uses the final state of the environment map, the context is created with simple authentication, not anonymous authentication. This is a genuine false positive of the syntactic rule. The pattern of setting a default configuration and then overriding it before use is realistic in real codebases, especially when applying a secure fix while leaving the old line intact. However, the code is not actually vulnerable, so the false positive does not represent a critical security issue; it is a precision/noise problem.
- LLM judge says issue: False
- Tool says issue: True

#### Reproduction Code

```java
import javax.naming.Context;
import javax.naming.directory.DirContext;
import javax.naming.directory.InitialDirContext;

public class Cls {
    public void ldapBind(Environment env) {
        // ruleid:anonymous-ldap-bind
        env.put(Context.SECURITY_AUTHENTICATION, "none");
        env.put(Context.SECURITY_AUTHENTICATION, "simple");
        DirContext ctx = new InitialDirContext(env);
    }
}
```

#### Oracle

```json
{
  "has_issue": false,
  "reason": "This mutation aims to be a secure variant and expose a potential false positive.",
  "expected_focus": "initial_dir_context_creation"
}
```

## Grouped Reportable Mutants (by Root Cause)

### Group 1: Missing overwrite/final-value tracking for the mutable JNDI environment map.
**Type**: TECHNIQUE
**Count**: 4

**Explanation**: Mutants 4, 9, 10, and 12 are false positives because the rule flags an initial `SECURITY_AUTHENTICATION` put of `"none"` but does not model a subsequent put that overwrites the same key with an authenticated mode (`"GSSAPI"` or `"simple"`). Fixing this requires data-flow/state tracking of the environment object to determine the final authentication value before `InitialDirContext` construction.

- 1. P1 · anonymous_authentication_configuration · false_positive · FP
  should_report=True llm_issue=False tool_issue=True
  bug=The analyzer reports an anonymous LDAP bind, but the code sets `SECURITY_AUTHENTICATION` to `"none"` and then immediately overwrites it with `"GSSAPI"` before creating the initial context, so the final configuration is authenticated. Thi...
- 2. P1 · environment_object_flow_and_ordering · false_positive · FP
  should_report=True llm_issue=False tool_issue=True
  bug=The static analyzer incorrectly reports an anonymous LDAP bind because it detects the initial put of SECURITY_AUTHENTICATION to "none" but fails to account for the subsequent put of "simple" that overwrites it before InitialDirContext is...
- 3. P1 · environment_object_flow_and_ordering · false_positive · FP
  should_report=True llm_issue=False tool_issue=True
  bug=The Semgrep rule anonymous-ldap-bind flags the pattern env.put(Context.SECURITY_AUTHENTICATION, "none") followed by new InitialDirContext(env). However, the rule is purely syntactic and does not model that the same key is subsequently ov...
- 4. P1 · initial_dir_context_creation · false_positive · FP
  should_report=True llm_issue=False tool_issue=True
  bug=The Semgrep rule flags an anonymous LDAP bind based on an earlier `put` of `SECURITY_AUTHENTICATION` to `"none"`, but the same environment key is overwritten with `"simple"` before the `InitialDirContext` is constructed. The final enviro...

### Group 2: Missing constant/expression propagation for JNDI property keys and authentication values.
**Type**: TECHNIQUE
**Count**: 3

**Explanation**: Mutants 1, 3, and 6 require resolving non-literal expressions to the canonical JNDI property key or the anonymous value `"none"`: [1] uses a conditional expression yielding `"none"`, [3] hides `java.naming.security.authentication` behind a named constant, and [6] passes a local variable initialized to `"none"`. The rule only matches the literal `Context.SECURITY_AUTHENTICATION` key and literal `"none"` value, so it needs constant/expression propagation and string equivalence.

- 1. P0 · anonymous_authentication_configuration · false_negative · FN
  should_report=True llm_issue=True tool_issue=False
  bug=The code sets the JNDI security authentication property to 'none' based on a conditional check, causing an anonymous LDAP bind when the authentication mode is empty or none. This allows unauthenticated users to perform LDAP operations, p...
- 2. P0 · anonymous_authentication_configuration · false_negative · FN
  should_report=True llm_issue=True tool_issue=False
  bug=The code configures JNDI LDAP authentication to anonymous mode by putting "java.naming.security.authentication" = "none" into the environment and then creating an InitialDirContext, causing an anonymous LDAP bind with no credentials. The...
- 3. P0 · environment_object_flow_and_ordering · false_negative · FN
  should_report=True llm_issue=True tool_issue=False
  bug=The environment property Context.SECURITY_AUTHENTICATION is set to "none", causing JNDI/LDAP to perform an anonymous bind with no credentials. This allows any unauthenticated attacker with network access to execute LDAP operations under ...

### Group 3: Missing control-flow/nested-block matching for the vulnerable `put` statement.
**Type**: TECHNIQUE
**Count**: 3

**Explanation**: Mutants 2, 5, and 8 are false negatives because the `env.put(Context.SECURITY_AUTHENTICATION, "none")` call is nested inside a `switch` or `if` block, while the vulnerable `InitialDirContext` construction occurs after the block. The rule's sequence pattern only matches statements at the same block level, so it misses puts that are control-flow dependent but still dominate the context construction.

- 1. P0 · anonymous_authentication_configuration · false_negative · FN
  should_report=True llm_issue=True tool_issue=False
  bug=The JNDI environment is configured with Context.SECURITY_AUTHENTICATION="none" and then used to create an InitialDirContext, causing an anonymous LDAP bind with no credentials. This disables authentication for the LDAP connection and can...
- 2. P0 · anonymous_authentication_configuration · false_positive · FN
  should_report=True llm_issue=True tool_issue=False
  bug=Setting JNDI SECURITY_AUTHENTICATION to "none" when credentials are missing configures an anonymous LDAP bind, which can permit unauthenticated attackers to perform LDAP operations under anonymous permissions.
- 3. P0 · environment_object_flow_and_ordering · false_negative · FN
  should_report=True llm_issue=True tool_issue=False
  bug=The JNDI environment is configured with SECURITY_AUTHENTICATION="none" before creating an InitialDirContext, causing the LDAP provider to perform an anonymous bind with no credentials. This allows unauthenticated access to the LDAP serve...

### Group 4: Missing `Properties.setProperty` API variant for environment property mutation.
**Type**: RULE_SPECIFIC
**Count**: 2

**Explanation**: Mutants 0 and 7 use `env.setProperty(...)` instead of `env.put(...)` to set the JNDI authentication property. For `Properties`-based environments, `setProperty` is equivalent to `put`, but the rule only matches `put`. This requires a rule-specific pattern addition for the `setProperty` API (and in [7], also handling the variable value, but the shared rule-level gap is the missing API variant).

- 1. P0 · anonymous_authentication_configuration · false_negative · FN
  should_report=True llm_issue=True tool_issue=False
  bug=The code configures JNDI LDAP authentication to anonymous mode using setProperty, causing an anonymous LDAP bind. The static analyzer only detects the put-based variant, so it fails to flag this semantically equivalent insecure authentic...
- 2. P0 · environment_object_flow_and_ordering · false_negative · FN
  should_report=True llm_issue=True tool_issue=False
  bug=The code disables LDAP authentication by setting the JNDI property java.naming.security.authentication to "none" on the environment object and constructing an InitialDirContext from it, causing an anonymous LDAP bind. Any unauthenticated...

### Group 5: Missing inline/chained `InitialDirContext` construction pattern.
**Type**: RULE_SPECIFIC
**Count**: 1

**Explanation**: Mutant 11 is a false negative because `new InitialDirContext(...)` is not assigned to a variable; it is immediately chained with `.getAttributes("")`. The rule requires the assignment form `$DCTX = new InitialDirContext($ENV, ...)`, so it needs a rule-specific pattern variant for directly used or chained constructor calls.

- 1. P0 · initial_dir_context_creation · false_negative · FN
  should_report=True llm_issue=True tool_issue=False
  bug=The environment object is configured with Context.SECURITY_AUTHENTICATION = "none" and then passed to `new InitialDirContext(...)`, causing the LDAP provider to perform an anonymous bind (CWE-287). Because the constructed context is imme...
