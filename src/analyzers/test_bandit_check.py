import pytest
from bandit_check import BanditAnalyzer
from pathlib import Path
import os

dataset_dir = Path(os.getenv("SAT_WORK_DIR")) / "dataset/bandit"

def test_bandit_checks():
    analyzer = BanditAnalyzer(dataset_dir)
    rule_ids = analyzer.get_all_rule_ids()
    print(f"Available Bandit rules: {rule_ids}")
    for rule_id in rule_ids:  # Test first 5 rules
        print(f"\nTesting rule: {rule_id}")
        test_cases = analyzer.load_test_cases(rule_id)
        for tn, tc in test_cases.items():
            print(f"  Running test case: {tn}")
            result = analyzer.run_check(rule_id, tn)
            if result.runtime_error:
                print(f"    Runtime error: {result.output}")
            assert result.issues_found, f"Expected 1 more issues for {tn}, but found none: {result.output}"

            result = analyzer.run_check_in_temp_dir(rule_id, tc)
            if result.runtime_error:
                print(f"    Runtime error: {result.output}")
            assert result.issues_found, f"Expected 1 more issues for temp test case, but found none: {result.output}"

if __name__ == "__main__":
    test_bandit_checks()