# Adding a New Analyzer

S-MRVA wraps each SAST tool behind a small **`Analyzer`** interface. To support a
new tool (e.g. Fortify, Infer, ESLint-security), implement that interface and
register it. The rest of the pipeline (analysis, query, synthesis, verification)
then works unchanged.

Files involved:

```
src/analyzers/
├── analyzer.py            # Analyzer base class + CheckResult
├── <tool>_check.py        # <Tool>Analyzer(Analyzer)   <- you add this
└── impl_<tool>_check.py   # thin CLI runner            <- and this
src/agents/pipeline_agent.py   # cli() registers the analyzer by name
```

---

## 1. The contract

```python
@dataclass
class CheckResult:
    test_id: str
    issues_found: bool      # did the TOOL flag this test as a finding?
    output: str             # raw tool output (kept for the report)
    runtime_error: bool     # True if the tool failed to run (case is dropped)

class Analyzer:
    def __init__(self, analyzer_name: str, dataset_dir: Path): ...
    def get_all_rule_ids(self) -> list[str]: ...
    def get_rule_description(self, rule_id: str) -> str: ...
    def load_rule(self, rule_id: str) -> dict[str, str]: ...       # {path: text}
    def load_test_cases(self, rule_id: str) -> dict[str, str]: ... # {path: text}
    def run_check(self, rule_id: str, test_path) -> CheckResult: ...
    def run_check_in_temp_dir(self, rule_id: str, test_code: str) -> CheckResult: ...
```

How the pipeline uses them (so you implement the right semantics):

| Method | Called by | Notes |
|---|---|---|
| `load_rule`, `load_test_cases`, `get_rule_description` | `analysis_agent` | Feeds the LLM that decomposes the rule. |
| `run_check_in_temp_dir` | `analysis_agent`, `verify_agent` | Run the tool on a synthesized snippet. **Called with keyword args** `rule_id=` and `test_code=`. |
| `.issues_found` | verifiers | Compared against the LLM judge → FP/FN. |
| `.runtime_error` | verifiers | If `True`, the case is excluded from FP/FN counts. |

Anything that is not a completed tool run **must** set `runtime_error=True`
(e.g. binary missing, timeout, parse failure), otherwise the case is
misinterpreted as a clean pass.

---

## 2. Step 1 — the runner (`impl_<tool>_check.py`)

Keep the actual process invocation isolated here so the `Analyzer` stays thin
and testable. It should return a plain dict:

```python
# src/analyzers/impl_mytool_check.py
import subprocess
from pathlib import Path

class MyToolRunner:
    def run(self, file_path: str, rule_id: str) -> dict:
        cmd = ["mytool", "--rule", rule_id, str(file_path)]
        try:
            p = subprocess.run(cmd, capture_output=True, text=True)
        except FileNotFoundError:
            return {"success": False, "issues_found": False, "output": "",
                    "error": "mytool is not installed"}
        output = (p.stdout or "") + "\n" + (p.stderr or "")
        return {"success": True, "issues_found": self._parse(output), "output": output}

    def _parse(self, output: str) -> bool:
        # Prefer the tool's JSON output; fall back to a "N findings" regex.
        return "finding" in output.lower()
```

See `impl_semgrep_check.py` / `SemgrepCheckRunner` for a full example.

## 3. Step 2 — the analyzer (`<tool>_check.py`)

```python
# src/analyzers/mytool_check.py
import os, tempfile
from pathlib import Path
from typing import Dict, List, Optional

try:                                  # S-MRVA runs with src/ on sys.path
    from analyzer import Analyzer, CheckResult
    from impl_mytool_check import MyToolRunner
except ImportError:
    from .analyzer import Analyzer, CheckResult
    from .impl_mytool_check import MyToolRunner

class MyToolAnalyzer(Analyzer):
    def __init__(self, dataset_dir: Optional[str] = None, language: str = "java"):
        super().__init__("mytool", dataset_dir)
        self.runner = MyToolRunner()
        self.language = language

    def get_all_rule_ids(self) -> List[str]:
        return os.listdir(self.dataset_dir)

    def get_rule_description(self, rule_id: str) -> str:
        return f"MyTool rule {rule_id}"        # or read it from the rule file

    def load_rule(self, rule_id: str) -> Dict[str, str]:
        d = Path(self.dataset_dir) / rule_id
        return {str(f): f.read_text() for f in d.glob("*.yaml")} if d.exists() else {}

    def load_test_cases(self, rule_id: str) -> Dict[str, str]:
        d = Path(self.dataset_dir) / rule_id
        if not d.exists():
            return {}
        return {str(f): f.read_text() for f in d.iterdir()
                if f.is_file() and f.suffix != ".yaml"}

    def run_check(self, rule_id: str, test_path) -> CheckResult:
        r = self.runner.run(file_path=str(test_path), rule_id=rule_id)
        return CheckResult(test_id=rule_id, issues_found=r.get("issues_found", False),
                           output=r.get("output", ""),
                           runtime_error=not r.get("success", False))

    _SUFFIX = {"python": ".py", "java": ".java", "javascript": ".js",
               "go": ".go", "c": ".c", "cpp": ".cpp"}

    def run_check_in_temp_dir(self, rule_id: str, test_code: str) -> CheckResult:
        suffix = self._SUFFIX.get(self.language, ".java")
        with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as f:
            f.write(test_code.encode()); path = f.name
        try:
            return self.run_check(rule_id, path)
        finally:
            os.unlink(path)
```

> Like `semgrep_check.py`, read `SAT_WORK_DIR` at import time if you need to
> resolve default dataset paths, and **raise** if it is unset.

## 4. Step 3 — register it

In `src/agents/pipeline_agent.py`, `cli()` selects the analyzer by name:

```python
elif args.analyzer == "mytool":
    from analyzers.mytool_check import MyToolAnalyzer
    analyzer = MyToolAnalyzer(dataset_dir=args.base_dir, language=args.language)
```

Update the `--analyzer` help string and the final `raise ValueError(...)` list.

## 5. Step 4 — dataset layout

Put rules under `dataset/<tool>-rules/<rule_id>/`, mirroring the built-ins:

```
dataset/mytool-rules/
└── my-rule-id/
    ├── my-rule-id.yaml      # the rule (load_rule)
    └── testcases.java       # seed tests (load_test_cases)
```

`--base_dir dataset/mytool-rules` then works with no code change.

## 6. Step 5 — Docker

Install the tool and put it on `PATH` in the `Dockerfile` (see how CodeQL and
SpotBugs are installed), and `COPY` the rule directory:

```dockerfile
RUN curl -fsSL <mytool-url> -o /tmp/mytool.zip && unzip -q /tmp/mytool.zip -d /opt/mytool
ENV PATH="/opt/mytool/bin:${PATH}"
COPY dataset/ dataset/     # already present
```

## 7. Step 6 — test

```bash
python3 src/agents/pipeline_agent.py \
  --rule_id my-rule-id --language java --analyzer mytool \
  --base_dir dataset/mytool-rules \
  --artifacts_dir example/output
```

A successful run writes
`example/output/my-rule-id/pipeline_report_my-rule-id.md` and
`pipeline_summary_my-rule-id.json` (same schema as the built-in analyzers). To
unit-test just the wrapper, mirror `src/analyzers/test_semgrep_check.py`.

---

## Gotchas

- **Keyword names**: `run_check_in_temp_dir(rule_id=..., test_code=...)` is
  called with keywords — keep those parameter names.
- **`runtime_error` discipline**: only a genuine tool run with a real verdict
  should be `runtime_error=False`; a missing binary or crash must be `True`.
- **`issues_found` is the tool's verdict**, not the judge's. The verifier
  compares the two, so do not pre-filter findings.
- **Language → file suffix** matters: the tool needs the right extension to
  parse the temporary snippet.
- **`SAT_WORK_DIR`** must be set (it is, in the Docker image and any `.env`).
