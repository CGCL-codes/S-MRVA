import pytest
from semgrep_check import SemgrepAnalyzer
import os
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed

dataset_dir = Path(os.getenv("SAT_WORK_DIR")) / "dataset/semgrep-rules"


def _check_single_case(rule_id: str, test_path: str, test_code: str):
    analyzer = SemgrepAnalyzer(dataset_dir=dataset_dir)
    failures = []
    expected_issue = "ruleid" in test_code.lower()
    try:
        result = analyzer.run_check(rule_id, test_path)
        if result.runtime_error:
            print(f"    Runtime error(run_check): {result.output}")
        if expected_issue and not result.issues_found:
            failures.append(f"Expected issues for {test_path}, but found none: {result.output}")
        if not expected_issue and result.issues_found:
            failures.append(f"Expected no issues for {test_path}, but found some: {result.output}")
    except Exception as e:
        print(f"    Unexpected message/run_check for {test_path}: {e}")
    return failures


def test_semgrep_check():
    analyzer = SemgrepAnalyzer(dataset_dir=dataset_dir)
    rule_ids = analyzer.get_all_rule_ids()
    print(rule_ids)
    assert len(rule_ids) > 0, "No rules found in Semgrep dataset"

    all_failures = []
    all_cases = []
    
    for rule_id in rule_ids:
        print(f"Testing rule: {rule_id}")
        rule_files = analyzer.load_rule(rule_id)
        assert len(rule_files) > 0, f"No rule files found for {rule_id}"
        
        test_cases = analyzer.load_test_cases(rule_id)
        assert len(test_cases) > 0, f"No test cases found for {rule_id}"

        for test_path, test_code in test_cases.items():
            all_cases.append((rule_id, str(test_path), test_code))

    max_workers = 30
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {
            executor.submit(_check_single_case, rule_id, test_path, test_code): (rule_id, test_path)
            for rule_id, test_path, test_code in all_cases
        }

        for future in as_completed(futures):
            rule_id, test_path = futures[future]
            failures = future.result()
            for failure in failures:
                all_failures.append(f"[{rule_id}] {failure}")


if __name__ == "__main__":
    test_semgrep_check()