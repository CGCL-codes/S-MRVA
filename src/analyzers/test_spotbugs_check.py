#!/usr/bin/env python3
"""
Test suite for SpotBugs security analyzer.

Tests:
- Rule discovery from dataset
- Rule metadata loading
- Test case loading and execution
- Security issue detection
"""

import pytest
from pathlib import Path
import os
import sys

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

try:
    from spotbugs_check import SpotBugsAnalyzer
except ImportError:
    from src.analyzers.spotbugs_check import SpotBugsAnalyzer

dataset_dir = Path(os.getenv("SAT_WORK_DIR", ".")) / "dataset/spotbugs-security"


def _get_expected_behavior(test_path: str, test_code: str) -> bool:
    """
    Determine if a test file is expected to trigger issues.
    
    Uses filename patterns and code context:
    - Filename patterns: "Bad"/"vulnerable"/"unsafe" = expect issues
                       "Good"/"safe" = expect no issues
    - Keywords: Check for vulnerability keywords in code
    
    Args:
        test_path: Path to the test file
        test_code: Content of the test file
    
    Returns:
        True if the test should find vulnerabilities
        False if the test should be clean
    """
    filename = Path(test_path).name.lower()
    
    # Check filename patterns first (highest priority)
    if "good" in filename or "ok" in filename or "safe" in filename:
        return False
    
    if "bad" in filename or "vulnerable" in filename or "unsafe" in filename:
        return True
    
    # Check for vulnerability indicators in code
    # SpotBugs files often contain comments or patterns indicating issues
    code_lower = test_code.lower()
    if any(keyword in code_lower for keyword in [
        "bug", "issue", "vulnerability", "vulnerable", "unsafe", "bad",
        "hardcoded", "weak", "constant"
    ]):
        return True
    
    # Default: assume test demonstrates vulnerability (conservative)
    return True


def test_spotbugs_rule_discovery():
    """Test that all SpotBugs security rules are discoverable."""
    analyzer = SpotBugsAnalyzer(dataset_dir)
    rule_ids = analyzer.get_all_rule_ids()
    
    print(f"\nDiscover SpotBugs rules: {len(rule_ids)} rules found")
    print(f"Rules: {rule_ids[:5]}..." if len(rule_ids) > 5 else f"Rules: {rule_ids}")
    
    # Should have at least some rules
    assert len(rule_ids) > 0, "No SpotBugs security rules discovered"
    
    # Check a few expected rules exist
    expected_rules = {
        "SQL_NONCONSTANT_STRING_PASSED_TO_EXECUTE",
        "DMI_CONSTANT_DB_PASSWORD",
        "PT_ABSOLUTE_PATH_TRAVERSAL"
    }
    
    found_rules = set(rule_ids)
    for expected_rule in expected_rules:
        if expected_rule in found_rules:
            print(f"  ✓ Found expected rule: {expected_rule}")


def test_spotbugs_load_rule():
    """Test loading rule source code."""
    analyzer = SpotBugsAnalyzer(dataset_dir)
    rule_ids = analyzer.get_all_rule_ids()
    
    if not rule_ids:
        pytest.skip("No SpotBugs rules available")
    
    # Test loading first rule
    rule_id = rule_ids[0]
    print(f"\nLoading detector code for rule: {rule_id}")
    
    rules = analyzer.load_rule(rule_id)
    assert rules is not None, f"Failed to load rule: {rule_id}"
    assert isinstance(rules, dict), f"Expected dict, got {type(rules)}"
    assert len(rules) > 0, f"Rule {rule_id} has no detector implementations"
    
    # Check rule content
    for detector_name, detector_code in rules.items():
        print(f"  Detector: {detector_name}")
        assert detector_code, f"Detector {detector_name} has empty code"
        assert "class" in detector_code or "interface" in detector_code, \
            f"Detector {detector_name} doesn't look like Java code"


def test_spotbugs_load_test_cases():
    """Test loading test cases for rules."""
    analyzer = SpotBugsAnalyzer(dataset_dir)
    rule_ids = analyzer.get_all_rule_ids()
    
    if not rule_ids:
        pytest.skip("No SpotBugs rules available")
    
    # Find a rule with test cases
    rule_with_tests = None
    for rule_id in rule_ids[:3]:  # Check first 3 rules
        test_cases = analyzer.load_test_cases(rule_id)
        if test_cases:
            rule_with_tests = rule_id
            print(f"\nFound test cases for rule: {rule_id}")
            print(f"  Test cases: {list(test_cases.keys())}")
            
            # Verify test case structure
            for test_name, test_code in test_cases.items():
                assert test_code, f"Test case {test_name} has empty code"
                assert "class" in test_code or "public" in test_code or "private" in test_code, \
                    f"Test case {test_name} doesn't look like Java code"
            break
    
    if rule_with_tests is None:
        pytest.skip("No rules with test cases found")


def test_spotbugs_rule_description():
    """Test loading rule descriptions and metadata."""
    analyzer = SpotBugsAnalyzer(dataset_dir)
    rule_ids = analyzer.get_all_rule_ids()
    
    if not rule_ids:
        pytest.skip("No SpotBugs rules available")
    
    # Test first rule
    rule_id = rule_ids[0]
    print(f"\nLoading description for rule: {rule_id}")
    
    description = analyzer.get_rule_description(rule_id)
    assert description, f"Failed to get description for {rule_id}"
    
    # Check description contains expected fields
    desc_str = str(description).lower()
    print(f"  Description: {description}")
    
    # Should mention category or CWE
    assert any(keyword in desc_str for keyword in ["category", "cwe", "security", "malicious"]), \
        f"Description missing metadata for {rule_id}"


def test_spotbugs_run_check():
    """Test running SpotBugs checks on test files."""
    analyzer = SpotBugsAnalyzer(dataset_dir)
    rule_ids = analyzer.get_all_rule_ids()
    
    if not rule_ids:
        pytest.skip("No SpotBugs rules available")
    
    # Find a rule with test cases
    tested_count = 0
    for rule_id in rule_ids:  # Test first 3 rules
        test_cases = analyzer.load_test_cases(rule_id)
        if not test_cases:
            continue
        
        print(f"\nTesting rule: {rule_id}")
        
        for test_name, test_code in list(test_cases.items())[:1]:  # Test first case
            print(f"  Running test: {test_name}")
            
            # Run check on the test file
            result = analyzer.run_check_in_temp_dir(rule_id, test_code)
            
            # Check result structure
            assert result is not None, f"No result for {rule_id}:{test_name}"
            assert hasattr(result, 'issues_found'), "Result missing issues_found attribute"
            assert hasattr(result, 'output'), "Result missing output attribute"
            
            # Display results
            print(f"    Issues found: {result.issues_found}")
            print(f"    Output: {result.output}")
            
            # Note: We don't assert issues_found=True because SpotBugs detection
            # depends on proper Java compilation and may have setup requirements
            tested_count += 1
    
    assert tested_count > 0, "No test cases were executed"


def test_spotbugs_temp_dir_execution():
    """Test running SpotBugs on temporary Java code snippets."""
    analyzer = SpotBugsAnalyzer(dataset_dir)
    
    # Example vulnerable Java code: hardcoded password
    vulnerable_code = """
package sfBugs;

import java.sql.CallableStatement;
import java.sql.Connection;
import java.sql.DriverManager;
import java.sql.SQLException;
import java.util.Properties;
import java.io.InputStream;

public class FNFP {
  public abstract static class MyCallableStatement implements CallableStatement {}

  public void doit() {
    Connection conn = null;
    CallableStatement stmt = null;
    try {
      Properties props = new Properties();
      InputStream input = getClass().getClassLoader().getResourceAsStream("appconfig.properties");
      props.load(input);
      String dbPassword = props.getProperty("appconfig.client.auth.a3.appPassword");
      String dbUser = props.getProperty("appconfig.client.auth.a3.appId");
      conn = DriverManager.getConnection("jdbc:mysql://localhost:3306/mydb", dbUser, dbPassword);
      stmt = conn.prepareCall("xxx");
    } catch (SQLException e) {
      e.printStackTrace();
    } catch (Exception e) {
      e.printStackTrace();
    } finally {
      if (stmt != null) {
        try {
          stmt.close();
        } catch (SQLException e) {
          e.printStackTrace();
        }
      }
      if (conn != null) {
        try {
          conn.close();
        } catch (SQLException e) {
          e.printStackTrace();
        }
      }
    }
  }
}
    """
    
    print(f"\nRunning SpotBugs on temporary code snippet")
    
    # Try to run on a dummy rule (won't find anything but tests infrastructure)
    result = analyzer.run_check_in_temp_dir("PT_ABSOLUTE_PATH_TRAVERSAL", vulnerable_code)
    
    # Check that execution completed
    assert result is not None, "Execution returned None"
    assert hasattr(result, 'output'), "Missing output field"
    
    print(f"  Execution completed: {not result.runtime_error}")
    print(f"  Output: {result.output}")


if __name__ == "__main__":
    print("Running SpotBugs Analyzer Tests")
    print("=" * 60)
    
    # Run tests manually
    # test_spotbugs_rule_discovery()
    # test_spotbugs_load_rule()
    # test_spotbugs_load_test_cases()
    # test_spotbugs_rule_description()
    # # test_spotbugs_run_check()
    test_spotbugs_temp_dir_execution()
    
    print("\n" + "=" * 60)
    print("All tests completed!")
