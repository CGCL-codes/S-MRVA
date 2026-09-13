#!/usr/bin/env python3
"""Simple pipeline test: run Semgrep on a seed test case for anonymous-ldap-bind."""

import os
import sys
import json
import subprocess
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

RULE_DIR = Path(__file__).parent.parent / "dataset" / "semgrep-rules" / "anonymous-ldap-bind"

def test_semgrep_on_rule():
    rule_file = RULE_DIR / "anonymous-ldap-bind.yaml"
    seed_file = RULE_DIR / "anonymous-ldap-bind_0.java"

    print(f"Rule: {rule_file}")
    print(f"Seed: {seed_file}")
    print()

    with open(rule_file) as f:
        print("=== Rule YAML ===")
        print(f.read()[:500])
    print()

    with open(seed_file) as f:
        print("=== Seed Test Case ===")
        print(f.read())
    print()

    print("=== Running Semgrep ===")
    result = subprocess.run(
        ["semgrep", "--config", str(rule_file), str(seed_file), "--json"],
        capture_output=True, text=True, timeout=60
    )

    try:
        output = json.loads(result.stdout)
        findings = output.get("results", [])
        print(f"Findings: {len(findings)}")
        for finding in findings:
            print(f"  - check_id: {finding.get('check_id')}")
            print(f"    message: {finding.get('extra', {}).get('message', 'N/A')}")
            print(f"    line: {finding.get('start', {}).get('line')}")
    except json.JSONDecodeError:
        print("JSON parse error. Raw output:")
        print(result.stdout[:1000])

    print()
    print("=== Negative test (clean code should NOT trigger) ===")
    clean_code = '''
import javax.naming.Context;
import javax.naming.directory.InitialDirContext;
import java.util.Properties;

public class Cls {
    public void ldapBind() throws Exception {
        Properties env = new Properties();
        env.put(Context.INITIAL_CONTEXT_FACTORY, "com.sun.jndi.ldap.LdapCtxFactory");
        env.put(Context.PROVIDER_URL, "ldap://localhost:389");
        env.put(Context.SECURITY_AUTHENTICATION, "simple");
        env.put(Context.SECURITY_PRINCIPAL, "cn=admin");
        env.put(Context.SECURITY_CREDENTIALS, "password");
        new InitialDirContext(env);
    }
}
'''
    tmp_file = Path("/tmp/test_clean.java")
    tmp_file.write_text(clean_code)
    result2 = subprocess.run(
        ["semgrep", "--config", str(rule_file), str(tmp_file), "--json"],
        capture_output=True, text=True, timeout=60
    )
    findings2 = json.loads(result2.stdout).get("results", [])
    print(f"Findings on clean code: {len(findings2)} (should be 0)")


if __name__ == "__main__":
    test_semgrep_on_rule()
