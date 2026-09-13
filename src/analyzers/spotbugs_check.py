import os
import shutil
import re
from pathlib import Path
from typing import Dict, List, Optional
import json

try: 
    from analyzer import Analyzer, CheckResult
    from impl_spotbugs_check import SpotBugsCheckRunner
except ImportError:
    from .analyzer import Analyzer, CheckResult
    from .impl_spotbugs_check import SpotBugsCheckRunner

dataset_dir = Path(os.getenv("SAT_WORK_DIR", ".")) / "dataset/spotbugs-security"
deps = dataset_dir / "compile_deps"

class SpotBugsAnalyzer(Analyzer):
    """Analyzer for SpotBugs security checks."""
    
    def __init__(self, dataset_dir: Optional[str] = None):
        super().__init__("spotbugs", dataset_dir or str(dataset_dir))
        self.runner = SpotBugsCheckRunner()
        self.language = "java"
    
    def get_all_rule_ids(self) -> List[str]:
        """
        Get list of all available SpotBugs security rules.
        
        Returns:
            List of rule IDs (directory names).
        """
        rule_dir = Path(self.dataset_dir)
        if not rule_dir.exists():
            return []
        rule_ids = [d.name for d in rule_dir.iterdir() if d.is_dir() and not d.name.startswith('_')]
        return sorted(rule_ids)
    
    def load_rule(self, rule_id: str) -> Dict[str, str]:
        """Load the content of a specific SpotBugs rule."""
        rule_path = Path(self.dataset_dir) / rule_id
        if not rule_path.exists():
            return {}
        
        rule_files = {}
        # Load .java detector implementation files
        for f in rule_path.glob("*.java"):
            if not f.name.startswith("test_"):
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
            if f.is_file() and f.suffix == ".java":
                test_cases[str(f)] = f.read_text()
        
        return test_cases
    
    def get_rule_description(self, rule_id: str) -> str:
        """Get a human-readable description of the rule."""
        rule_path = Path(self.dataset_dir) / rule_id
        metadata_file = rule_path / "metadata.json"
        
        if metadata_file.exists():
            try:
                metadata = json.loads(metadata_file.read_text())
                rule = metadata.get("rule", {})
                category = rule.get("category", "")
                cweid = rule.get("cweid", "")
                detectors = rule.get("detectors", [])
                
                desc = f"SpotBugs Rule: {rule_id}\n"
                desc += f"Category: {category}\n"
                if cweid:
                    desc += f"CWE: {cweid}\n"
                if detectors:
                    desc += f"Detectors: {', '.join([d.get('class_short', '') for d in detectors])}\n"
                return desc
            except:
                pass
        
        return "See the test_files directory for examples of this SpotBugs security rule."
    
    def run_check(self, rule_id: str, test_path: str) -> CheckResult:
        """
        Run a specific SpotBugs check on a test file.
        
        Args:
            rule_id: The rule ID (bug type)
            test_path: Path to the test Java file
        
        Returns:
            CheckResult object
        """
        rule_dir = Path(self.dataset_dir) / rule_id
        if not rule_dir.exists():
            raise ValueError(f"Rule directory not found: {rule_dir}")
        
        result = self.runner.run_spotbugs_check(
            file_path=test_path,
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
        Run a specific SpotBugs check on test code in a temporary directory.
        
        Args:
            rule_id: The rule ID
            test_code: Java source code as a string
        
        Returns:
            CheckResult object
        """
        import tempfile
        import shutil
        
        # Extract class name from test code
        class_name = self._extract_class_name(test_code)
        if not class_name:
            class_name = "TestClass"
        
        if not class_name.endswith(".java"):
            class_name = class_name + ".java"
        
        # Create a temporary directory
        temp_dir = tempfile.mkdtemp(prefix="spotbugs_test_")
        try:
            tmp_file_path = os.path.join(temp_dir, class_name)
            with open(tmp_file_path, 'w') as f:
                f.write(test_code)
            
            result = self.runner.run_spotbugs_check(
                file_path=tmp_file_path,
                rule_id=rule_id,
            )
        finally:
            # Clean up temporary directory
            try:
                shutil.rmtree(temp_dir)
            except:
                pass
        
        issues_found = result.get('issues_found', False)
        output = self.runner.format_results(result, verbose=True)
        runtime_error = not result.get('success', False)
        
        return CheckResult(
            test_id=rule_id,
            issues_found=issues_found,
            output=output,
            runtime_error=runtime_error
        )
    
    def _extract_class_name(self, java_code: str) -> str:
        """Extract public class name from Java source code."""
        import re
        match = re.search(r'public\s+(?:class|interface)\s+(\w+)', java_code)
        if match:
            return match.group(1)
        return "TestClass"
