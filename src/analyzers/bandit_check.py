import os
from pathlib import Path
from typing import Dict, List, Optional
import json

try: 
    from analyzer import Analyzer, CheckResult
    from impl_bandit_check import BanditCheckRunner
except ImportError:
    from .analyzer import Analyzer, CheckResult
    from .impl_bandit_check import BanditCheckRunner

dataset_dir = Path(os.getenv("SAT_WORK_DIR")) / "dataset/bandit"

class BanditAnalyzer(Analyzer):
    """Analyzer for Bandit security checks."""
    def __init__(self, dataset_dir: str = str(dataset_dir)):
        super().__init__("bandit", dataset_dir)
        self.runner = BanditCheckRunner()
    
    def get_all_rule_ids(self) -> List:
        """
        Get list of all available Bandit rules.
        
        Returns:
            List of rule dictionaries with metadata.
        """
        rule_ids = os.listdir(self.dataset_dir)
        return rule_ids
    
    def load_rule(self, rule_id: str) -> Dict[str, str]:
        rule_path = self.dataset_dir / rule_id
        return {rule_path / f: (rule_path / f).read_text() for f in os.listdir(rule_path) if f.endswith('.py')}

    def load_test_cases(self, rule_id: str) -> Dict[str, str]:
        rule_path = self.dataset_dir / rule_id
        test_path = rule_path / "test_files"
        return {test_path / f: (test_path / f).read_text() for f in os.listdir(test_path) if os.path.isfile(test_path / f)}
    
    def get_rule_description(self, rule_id: str) -> str:
        return "See the comment in the plugin file for a description of the rule."
    
    def run_check(self, rule_id: str, test_path: str) -> CheckResult:
        """Run a specific Bandit check on a test file."""
        result = self.runner.run_bandit_check(test_path, test_id=rule_id)
        issues_found = result.get('issues_found', False)
        output = self.runner.format_results(result, verbose=True)
        runtime_error = not result.get('success', False)
        
        return CheckResult(
            test_id=rule_id,
            issues_found=issues_found,
            output=output,
            runtime_error=runtime_error
        )

    def run_check_in_temp_dir(self, rule_id: str, test_code: str) -> CheckResult:
        """Run a specific Bandit check on test code in a temporary directory."""
        import tempfile
        with tempfile.NamedTemporaryFile(suffix=".py", delete=False) as tmp_file:
            tmp_file.write(test_code.encode())
            tmp_file.flush()
            tmp_file_path = tmp_file.name
            result = self.runner.run_bandit_check(
                file_path=tmp_file_path,
                test_id=rule_id,
            )
        issues_found = result.get('issues_found', False)
        output = self.runner.format_results(result)
        runtime_error = not result.get('success', False)
        
        return CheckResult(
            test_id=rule_id,
            issues_found=issues_found,
            output=output,
            runtime_error=runtime_error
        )


