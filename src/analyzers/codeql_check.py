import os
from pathlib import Path
from typing import Dict, List, Optional
import json

try: 
    from analyzer import Analyzer, CheckResult
    from impl_codeql_check import CodeQLCheckRunner
except ImportError:
    from .analyzer import Analyzer, CheckResult
    from .impl_codeql_check import CodeQLCheckRunner

dataset_dir = Path(os.getenv("SAT_WORK_DIR", ".")) / "dataset/codeql-rules"

class CodeQLAnalyzer(Analyzer):
    """Analyzer for CodeQL security checks."""
    
    def __init__(self, dataset_dir: Optional[str] = None, language: str = "python"):
        super().__init__("codeql", dataset_dir or str(dataset_dir))
        self.runner = CodeQLCheckRunner(language=language)
        self.language = language
    
    def get_all_rule_ids(self) -> List[str]:
        """
        Get list of all available CodeQL rules.
        
        Returns:
            List of rule IDs.
        """
        rule_dir = Path(self.dataset_dir)
        if not rule_dir.exists():
            return []
        rule_ids = [d.name for d in rule_dir.iterdir() if d.is_dir()]
        return rule_ids
    
    def load_rule(self, rule_id: str) -> Dict[str, str]:
        """Load the content of a specific CodeQL rule."""
        rule_path = Path(self.dataset_dir) / rule_id
        if not rule_path.exists():
            return {}
        
        rule_files = {}
        # Load .ql files as rules
        for f in rule_path.glob("*.ql"):
            rule_files[str(f)] = f.read_text()
        
        return rule_files

    def load_test_cases(self, rule_id: str) -> Dict[str, str]:
        """Load test cases for a specific rule."""
        rule_path = Path(self.dataset_dir) / rule_id
        test_path = rule_path / "test_files"
        if not test_path.exists():
            return {}
        
        test_cases = {}
        for f in test_path.iterdir():
            if f.is_file():
                test_cases[str(f)] = f.read_text()
        
        return test_cases
    
    def get_rule_description(self, rule_id: str) -> str:
        """Get a human-readable description of the rule."""
        return "See the CodeQL query file (.ql) for a description of the rule."
    
    def run_check(self, rule_id: str, test_path: str) -> CheckResult:
        """
        Run a specific CodeQL check on a test file.
        
        Args:
            rule_id: The rule ID
            test_path: Path to the test file
        
        Returns:
            CheckResult object
        """
        rule_dir = Path(self.dataset_dir) / rule_id
        if not rule_dir.exists():
            raise ValueError(f"Rule directory not found: {rule_dir}")
        
        result = self.runner.run_codeql_check(
            file_path=test_path,
            rule_dir=str(rule_dir),
            rule_id=rule_id
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
        Run a specific CodeQL check on test code in a temporary directory.
        
        Args:
            rule_id: The rule ID
            test_code: The test code content
        
        Returns:
            CheckResult object
        """
        import tempfile
        import os
        
        # Determine file extension based on language
        ext = ".py"
        filename = "test_code" + ext
        
        # Create a temporary directory for the code
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create a source subdirectory
            src_dir = os.path.join(temp_dir, "src")
            os.makedirs(src_dir, exist_ok=True)
            
            # Write the test code to a file in the temp directory
            test_file_path = os.path.join(src_dir, filename)
            with open(test_file_path, 'w') as f:
                f.write(test_code)
            
            rule_dir = Path(self.dataset_dir) / rule_id
            if not rule_dir.exists():
                raise ValueError(f"Rule directory not found: {rule_dir}")
            
            result = self.runner.run_codeql_check(
                file_path=test_file_path,
                rule_dir=str(rule_dir),
                rule_id=rule_id
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
