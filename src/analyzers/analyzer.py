from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional

@dataclass
class CheckResult:
    """Structured result from a check."""
    test_id: str
    issues_found: bool
    output: str
    runtime_error: bool

class Analyzer:
    analzer_name: str
    dataset_dir: Path

    def __init__(self, analyzer_name: str, dataset_dir: Path):
        self.analyzer_name = analyzer_name
        self.dataset_dir = Path(dataset_dir)

    def get_all_rule_ids(self) -> List[str]:
        """Get a list of all available rule IDs."""
        raise NotImplementedError("Subclasses should implement this method.")
    
    def get_rule_description(self, rule_id: str) -> str:
        """Get a human-readable description of the rule."""
        raise NotImplementedError("Subclasses should implement this method.")

    def load_rule(self, rule_id: str) -> Dict[str, str]:
        """Load the content of a specific rule by its ID."""
        raise NotImplementedError("Subclasses should implement this method.")
    
    def load_test_cases(self, rule_id: str) -> Dict[str, str]:
        raise NotImplementedError("Subclasses should implement this method.")
    
    def run_check(self, rule_id: str, test_path: Path) -> CheckResult:
        raise NotImplementedError("Subclasses should implement this method.")
    
    def run_check_in_temp_dir(self, rule_id: str, test_code: str) -> CheckResult:
        raise NotImplementedError("Subclasses should implement this method.")