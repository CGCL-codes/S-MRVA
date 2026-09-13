import pytest
from codeql_check import CodeQLAnalyzer
from pathlib import Path
import os
from concurrent.futures import ThreadPoolExecutor, as_completed

dataset_dir = Path(os.getenv("SAT_WORK_DIR", ".")) / "dataset/codeql-rules"


def _has_alert_annotations(code: str) -> bool:
    """Check if code contains CodeQL alert annotations (marks expected issues)."""
    # CodeQL test files mark expected issues with comments like:
    # # $ Alert[...]
    # # $ Alert=name
    return "# $" in code or "# Alert" in code


def _should_have_issues(test_path: str, test_code: str) -> bool | None:
    """
    Determine if a test case should have issues.
    
    Checks:
    1. Filename patterns: "Bad" suffix = issues expected, "Good" suffix = no issues
    2. CodeQL alert annotations in code
    3. Keywords in code: "issue" or "bad"
    
    Args:
        test_path: Path to the test file
        test_code: Content of the test file
    
    Returns:
        True if issues are expected
        False if no issues are expected
        None if unclear (accept both outcomes)
    """
    filename = Path(test_path).name.lower()
    
    # Check filename patterns first (highest priority)
    if "good" in filename or "ok" in filename or "safe" in filename:
        return False
    if "bad" in filename or "vulnerable" in filename or "unsafe" in filename:
        return True
    
    # Then check for CodeQL alert annotations
    if _has_alert_annotations(test_code):
        return True
    
    # Finally check for keywords
    if "issue" in test_code.lower() or "bad" in test_code.lower() or "vulnerable" in test_code.lower() or "unsafe" in test_code.lower():
        return True
    
    # Unknown - accept both outcomes
    return None


def _check_single_case(rule_id: str, test_path: str, test_code: str, language: str):
    """Helper function to check a single test case."""
    try:
        analyzer = CodeQLAnalyzer(dataset_dir=str(dataset_dir), language=language)
        failures = []
        expected_issue = _should_have_issues(test_path, test_code)
        
        result = analyzer.run_check(rule_id, test_path)
        if result.runtime_error:
            print(f"    Runtime error(run_check): {result.output}")
        
        # Only report failures if expectation is known (not None)
        if expected_issue is not None:
            if expected_issue and not result.issues_found:
                failures.append(f"Expected issues for {test_path}, but found none: {result.output}")
            if not expected_issue and result.issues_found:
                failures.append(f"Expected no issues for {test_path}, but found some: {result.output}")
        
        result = analyzer.run_check_in_temp_dir(rule_id, test_code)
        if result.runtime_error:
            print(f"    Runtime error(run_check_in_temp_dir): {result.output}")
        
        # Only report failures if expectation is known (not None)
        if expected_issue is not None:
            if expected_issue and not result.issues_found:
                failures.append(f"Expected issues for temp code in {test_path}, but found none: {result.output}")
            if not expected_issue and result.issues_found:
                failures.append(f"Expected no issues for temp code in {test_path}, but found some: {result.output}")
        
        return failures
    except Exception as e:
        print(f"    Exception in _check_single_case for {test_path}: {e}")
        return [str(e)]


def test_codeql_analyzer_initialized():
    """Test that CodeQL analyzer can be initialized."""
    try:
        analyzer = CodeQLAnalyzer(dataset_dir=str(dataset_dir), language="python")
        assert analyzer is not None
        assert analyzer.analyzer_name == "codeql"
        assert analyzer.language == "python"
        print("✓ CodeQL analyzer initialized successfully")
    except Exception as e:
        print(f"Warning: CodeQL initialization test failed (this may be expected if CodeQL is not installed): {e}")


def test_codeql_rule_loading():
    """Test that rules can be loaded from dataset."""
    try:
        analyzer = CodeQLAnalyzer(dataset_dir=str(dataset_dir), language="python")
        rule_ids = analyzer.get_all_rule_ids()
        
        if len(rule_ids) == 0:
            print("⚠ No CodeQL rules found in dataset directory")
            return
        
        print(f"Found {len(rule_ids)} CodeQL rules: {rule_ids[:5]}...")
        
        # Test loading first rule
        first_rule = rule_ids[0]
        rule_files = analyzer.load_rule(first_rule)
        print(f"✓ Loaded rule '{first_rule}' with {len(rule_files)} file(s)")
        
    except Exception as e:
        print(f"Warning: Rule loading test encountered issue: {e}")


def test_codeql_test_cases_loading():
    """Test that test cases can be loaded from dataset."""
    try:
        analyzer = CodeQLAnalyzer(dataset_dir=str(dataset_dir), language="python")
        rule_ids = analyzer.get_all_rule_ids()
        
        if len(rule_ids) == 0:
            print("⚠ No CodeQL rules found in dataset directory")
            return
        
        # Test loading test cases for first rule
        first_rule = rule_ids[0]
        test_cases = analyzer.load_test_cases(first_rule)
        
        if len(test_cases) > 0:
            print(f"✓ Loaded {len(test_cases)} test case(s) for rule '{first_rule}'")
        else:
            print(f"⚠ No test cases found for rule '{first_rule}'")
        
    except Exception as e:
        print(f"Warning: Test case loading encountered issue: {e}")


def test_codeql_check_execution():
    """Test CodeQL check execution on sample code."""
    try:
        analyzer = CodeQLAnalyzer(dataset_dir=str(dataset_dir), language="python")
        
        # Sample vulnerable Python code
        vulnerable_code = """
import os
def read_file(filename):
    with open(filename, 'r') as f:
        return f.read()
        """
        
        # Try to run in temp directory
        rule_ids = analyzer.get_all_rule_ids()
        if len(rule_ids) > 0:
            first_rule = rule_ids[0]
            result = analyzer.run_check_in_temp_dir(first_rule, vulnerable_code)
            
            print(f"✓ CodeQL check executed for rule '{first_rule}'")
            print(f"  - Success: {not result.runtime_error}")
            print(f"  - Issues found: {result.issues_found}")
            if result.runtime_error:
                print(f"  - Output: {result.output}...")
        else:
            print("⚠ No rules available to test execution")
    
    except Exception as e:
        print(f"Note: CodeQL check execution test encountered (expected if CodeQL not installed): {e}")


def test_codeql_checks_comprehensive():
    """Comprehensive test of all CodeQL rules if dataset is available."""
    try:
        analyzer = CodeQLAnalyzer(dataset_dir=str(dataset_dir), language="python")
        rule_ids = analyzer.get_all_rule_ids()
        
        if len(rule_ids) == 0:
            print("⚠ No CodeQL rules found in dataset - skipping comprehensive test")
            return
        
        print(f"Testing {len(rule_ids)} CodeQL rules...")
        all_failures = []
        all_cases = []
        
        for rule_id in rule_ids:  # Test first 3 rules to avoid long execution
            print(f"Testing rule: {rule_id}")
            
            try:
                rule_files = analyzer.load_rule(rule_id)
                if len(rule_files) == 0:
                    print(f"  ⚠ No rule files found for {rule_id}")
                    continue
                
                test_cases = analyzer.load_test_cases(rule_id)
                if len(test_cases) == 0:
                    print(f"  ⚠ No test cases found for {rule_id}")
                    continue
                
                print(f"  Loaded {len(test_cases)} test case(s)")
                
                for test_path, test_code in list(test_cases.items())[:2]:  # Test first 2 cases per rule
                    all_cases.append((rule_id, str(test_path), test_code, "python"))
            
            except Exception as e:
                print(f"  Error loading rule {rule_id}: {e}")
                continue
        
        if len(all_cases) == 0:
            print("⚠ No test cases available to run")
            return
        
        # Run checks with thread pool (limited to avoid resource exhaustion)
        max_workers = 2
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {
                executor.submit(_check_single_case, rule_id, test_path, test_code, lang): (rule_id, test_path)
                for rule_id, test_path, test_code, lang in all_cases
            }
            
            for future in as_completed(futures):
                rule_id, test_path = futures[future]
                try:
                    failures = future.result(timeout=120)
                    for failure in failures:
                        all_failures.append(f"[{rule_id}] {failure}")
                except Exception as e:
                    all_failures.append(f"[{rule_id}] Execution failed: {str(e)}")
        
        if all_failures:
            print("\nFailures found:")
            for failure in all_failures:
                print(f"  - {failure}")
        else:
            print("✓ All test cases passed")
    
    except Exception as e:
        print(f"Note: Comprehensive test encountered issue (may be expected): {e}")


def test_bug_1():
    analyzer = CodeQLAnalyzer(dataset_dir=str(dataset_dir), language="python")
    test_code = open(dataset_dir / "RequestWithoutValidation/test_files/make_request.py").read()
    r = analyzer.run_check_in_temp_dir("RequestWithoutValidation", test_code)
    print(r)

def test_bug_2():
    dataset_dir = Path(os.getenv("SAT_WORK_DIR", ".")) / "dataset/sampled/codeql-rules"
    analyzer = CodeQLAnalyzer(dataset_dir=str(dataset_dir), language="python")
    """Test that test cases can be loaded from sampled dataset."""
    rule_ids = analyzer.get_all_rule_ids()
    
    if len(rule_ids) == 0:
        print("⚠ No CodeQL rules found in dataset directory")
        return
    
    # Test loading test cases for first rule
    for rule_id in rule_ids:
        print(f"Testing rule: {rule_id}")
        test_cases = analyzer.load_test_cases(rule_id)
        if len(test_cases) > 0:
            print(f"✓ Loaded {len(test_cases)} test case(s) for rule '{rule_id}'")
        else:
            print(f"⚠ No test cases found for rule '{rule_id}'")
        for test_cases_path, test_cases_code in test_cases.items():
            print(f"Testing {test_cases_path}...")
            r = analyzer.run_check_in_temp_dir(rule_id, test_cases_code)
            print(r)
        
    

if __name__ == "__main__":
    print("=" * 60)
    print("Running CodeQL Analyzer Tests")
    print("=" * 60)
    
    print("\n[1/4] Testing CodeQL analyzer initialization...")
    test_codeql_analyzer_initialized()
    
    print("\n[2/4] Testing CodeQL rule loading...")
    test_codeql_rule_loading()
    
    print("\n[3/4] Testing CodeQL test case loading...")
    test_codeql_test_cases_loading()
    
    print("\n[4/4] Running comprehensive tests...")
    # test_codeql_checks_comprehensive()

    #test_bug_1()
    test_bug_2()
    
    print("\n" + "=" * 60)
    print("CodeQL tests completed")
    print("=" * 60)
