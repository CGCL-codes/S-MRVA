import os
from pathlib import Path
from typing import Dict, List, Optional
import json

try:
    from analyzer import Analyzer, CheckResult
    from impl_semgrep_check import SemgrepCheckRunner
except ImportError:
    from .analyzer import Analyzer, CheckResult
    from .impl_semgrep_check import SemgrepCheckRunner

work_dir = os.getenv("SAT_WORK_DIR")
if not work_dir:    raise EnvironmentError("Environment variable SAT_WORK_DIR is not set.")

dataset_dir = Path(work_dir) / "dataset/semgrep-rules"

class SemgrepAnalyzer(Analyzer):
    """Analyzer for Semgrep security checks."""
    
    def __init__(self, dataset_dir: Optional[str] = None, language: str = "java"):
        super().__init__("semgrep", dataset_dir)
        self.runner = SemgrepCheckRunner()
        self.language = language
    
    def get_all_rule_ids(self) -> List[str]:
        return os.listdir(self.dataset_dir)
    
    def load_rule(self, rule_id: str) -> Dict[str, str]:
        rule_path = self.dataset_dir / rule_id
        if not rule_path.exists():
            return {}
        
        rule_files = {}
        for f in rule_path.glob("*.yaml"):
            if f.stem == rule_id:
                rule_files[str(f)] = f.read_text()
                # single file rule
                break
        
        return rule_files
    
    def load_test_cases(self, rule_id: str) -> Dict[str, str]:
        rule_path = self.dataset_dir / rule_id
        if not rule_path.exists():
            return {}
        
        test_cases = {}
        # Load all non-yaml files as test cases
        for f in rule_path.iterdir():
            if f.is_file() and not f.name.endswith('.yaml'):
                test_cases[str(f)] = f.read_text()
        
        return test_cases
    
    def get_rule_description(self, rule_id: str) -> str:
        return "See the description and metadata in the YAML file for a description of the rule."
    
    def run_check(self, rule_id: str, test_path: str) -> CheckResult:
        """
        Run a specific Semgrep check on a test file.
        
        Args:
            rule_id: The rule ID
            test_path: Path to the test file
        
        Returns:
            CheckResult object
        """
        rule_path = self.dataset_dir / rule_id / f"{rule_id}.yaml"
        if not rule_path.exists():
            raise ValueError(f"Rule file not found: {rule_path}")

        result = self.runner.run_semgrep_check(
            file_path=test_path,
            rule_path=rule_path
        )
        
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
        """
        Run a specific Semgrep check on test code in a temporary directory.
        
        Args:
            rule_id: The rule ID
            test_code: The test code content
        
        Returns:
            CheckResult object
        """
        rule_path = self.dataset_dir / rule_id / f"{rule_id}.yaml"
        if not rule_path.exists():
            raise ValueError(f"Rule file not found: {rule_path}")

        subfix_map = {
            "python": ".py",
            "java": ".java",
            "javascript": ".js",
            "go": ".go",
            "ruby": ".rb",
            "c": ".c",
            "cpp": ".cpp",
        }
        suffix = subfix_map.get(self.language, ".java")
        import tempfile
        with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp_file:
            tmp_file.write(test_code.encode())
            tmp_file.flush()
            tmp_file_path = tmp_file.name
            result = self.runner.run_semgrep_check(
                file_path=tmp_file_path,
                rule_path=rule_path
            )
        
        issues_found = result.get('issues_found', False)
        output = self.runner.format_results(result, verbose=True)
        runtime_error = not result.get('success', False)
        
        return CheckResult(
            test_id=rule_id,
            issues_found=issues_found,
            output=output,
            runtime_error=runtime_error
        )
