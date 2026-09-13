import json
import os
from pathlib import Path

import pytest

try:
    from pipeline_agent import PipelineAgent
except ImportError:
    from .pipeline_agent import PipelineAgent

try:
    from agents.model import llm
except ImportError:
    from .model import llm

try:
    from analyzers.bandit_check import BanditAnalyzer
    from analyzers.semgrep_check import SemgrepAnalyzer
    from analyzers.codeql_check import CodeQLAnalyzer
    from analyzers.spotbugs_check import SpotBugsAnalyzer
except ImportError:
    from ..analyzers.bandit_check import BanditAnalyzer
    from ..analyzers.semgrep_check import SemgrepAnalyzer
    from ..analyzers.codeql_check import CodeQLAnalyzer
    from ..analyzers.spotbugs_check import SpotBugsAnalyzer


WORKSPACE_ROOT = Path(__file__).resolve().parents[2]


@pytest.mark.integration
def test_pipeline_bandit_b501_generates_report():
    DATASET_DIR = WORKSPACE_ROOT / "dataset" / "bandit"
    ARTIFACTS_DIR = WORKSPACE_ROOT / "output"
    RULE_ID = "B501"
    if not os.getenv("DASHSCOPE_API_KEY"):
        pytest.skip("DASHSCOPE_API_KEY is required for the pipeline integration test")

    if not DATASET_DIR.exists():
        pytest.skip(f"Bandit dataset not found: {DATASET_DIR}")

    analyzer = BanditAnalyzer(dataset_dir=str(DATASET_DIR))
    result = PipelineAgent(
        llm=llm,
        analyzer=analyzer,
        language="python",
    ).run(rule_id=RULE_ID)

    summary = result.get("pipeline_summary", {})
    markdown_report = result.get("markdown_report", "")

    assert summary, "Expected a non-empty pipeline summary"
    assert summary.get("rule_id") == RULE_ID
    assert summary.get("language") == "python"
    assert isinstance(summary.get("stats"), dict)
    assert "all_variants_generated" in summary
    assert "all_reported_mutants_before_dedup" in summary
    assert "all_reported_mutants_after_dedup" in summary
    assert "reports" in summary

    stats = summary["stats"]
    assert stats.get("total_mutants_generated", 0) >= 0
    assert stats.get("total_verified", 0) >= 0
    assert stats.get("total_reportable_before_dedup", 0) >= stats.get(
        "total_reportable_after_dedup", 0
    )

    assert isinstance(markdown_report, str)
    assert f"# Static Rule Testing Report: {RULE_ID}" in markdown_report
    assert "## Original Rule Implementation" in markdown_report
    assert "## Original Seed Test Case" in markdown_report

    ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)
    summary_path = ARTIFACTS_DIR / f"pipeline_summary_{RULE_ID}.json"
    report_path = ARTIFACTS_DIR / f"pipeline_report_{RULE_ID}.md"

    summary_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    report_path.write_text(markdown_report, encoding="utf-8")

    assert summary_path.exists()
    assert report_path.exists()

@pytest.mark.integration
def test_pipeline_semgrep_tainted_env_from_http_request_generates_report():
    DATASET_DIR = WORKSPACE_ROOT / "dataset" / "semgrep-rules"
    ARTIFACTS_DIR = WORKSPACE_ROOT / "output"
    RULE_ID = "tainted-env-from-http-request"

    if not os.getenv("DASHSCOPE_API_KEY"):
        pytest.skip("DASHSCOPE_API_KEY is required for the pipeline integration test")

    analyzer = SemgrepAnalyzer(dataset_dir=str(DATASET_DIR))
    result = PipelineAgent(
        llm=llm,
        analyzer=analyzer,
        language="java",
    ).run(rule_id=RULE_ID)

    summary = result.get("pipeline_summary", {})
    markdown_report = result.get("markdown_report", "")

    assert summary, "Expected a non-empty pipeline summary"
    assert summary.get("rule_id") == RULE_ID
    assert summary.get("language") == "java"

    assert isinstance(markdown_report, str)
    assert f"# Static Rule Testing Report: {RULE_ID}" in markdown_report

    ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)
    summary_path = ARTIFACTS_DIR / f"pipeline_summary_{RULE_ID}.json"
    report_path = ARTIFACTS_DIR / f"pipeline_report_{RULE_ID}.md"

    summary_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    report_path.write_text(markdown_report, encoding="utf-8")

    assert summary_path.exists()
    assert report_path.exists()

@pytest.mark.integration
def test_pipeline_codeql_generates_report():
    DATASET_DIR = WORKSPACE_ROOT / "dataset" / "codeql-rules"
    ARTIFACTS_DIR = WORKSPACE_ROOT / "output"
    
    # Get first available rule from codeql-rules if it exists
    if not DATASET_DIR.exists():
        pytest.skip(f"CodeQL dataset not found: {DATASET_DIR}")
    
    rule_ids = [d.name for d in DATASET_DIR.iterdir() if d.is_dir()]
    if not rule_ids:
        pytest.skip("No CodeQL rules found in dataset")
    
    RULE_ID = rule_ids[0]  # Test with the first available rule
    
    if not os.getenv("DASHSCOPE_API_KEY"):
        pytest.skip("DASHSCOPE_API_KEY is required for the pipeline integration test")

    analyzer = CodeQLAnalyzer(dataset_dir=str(DATASET_DIR), language="python")
    result = PipelineAgent(
        llm=llm,
        analyzer=analyzer,
        language="python",
    ).run(rule_id=RULE_ID)

    summary = result.get("pipeline_summary", {})
    markdown_report = result.get("markdown_report", "")

    assert summary, "Expected a non-empty pipeline summary"
    assert summary.get("rule_id") == RULE_ID
    assert summary.get("language") == "python"
    assert isinstance(summary.get("stats"), dict)

    assert isinstance(markdown_report, str)
    assert f"# Static Rule Testing Report: {RULE_ID}" in markdown_report

    ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)
    summary_path = ARTIFACTS_DIR / f"pipeline_summary_{RULE_ID}.json"
    report_path = ARTIFACTS_DIR / f"pipeline_report_{RULE_ID}.md"

    summary_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    report_path.write_text(markdown_report, encoding="utf-8")

    assert summary_path.exists()
    assert report_path.exists()

@pytest.mark.integration
def test_pipeline_spotbugs_sql_injection_generates_report():
    """Test SpotBugs analyzer with SQL_NONCONSTANT_STRING_PASSED_TO_EXECUTE rule."""
    DATASET_DIR = WORKSPACE_ROOT / "dataset" / "spotbugs-security"
    ARTIFACTS_DIR = WORKSPACE_ROOT / "output"
    RULE_ID = "SQL_NONCONSTANT_STRING_PASSED_TO_EXECUTE"
    
    if not os.getenv("DASHSCOPE_API_KEY"):
        pytest.skip("DASHSCOPE_API_KEY is required for the pipeline integration test")
    
    if not DATASET_DIR.exists():
        pytest.skip(f"SpotBugs dataset not found: {DATASET_DIR}")
    
    analyzer = SpotBugsAnalyzer(dataset_dir=str(DATASET_DIR))
    result = PipelineAgent(
        llm=llm,
        analyzer=analyzer,
        language="java",
    ).run(rule_id=RULE_ID)

    summary = result.get("pipeline_summary", {})
    markdown_report = result.get("markdown_report", "")

    assert summary, "Expected a non-empty pipeline summary"
    assert summary.get("rule_id") == RULE_ID
    assert summary.get("language") == "java"
    assert isinstance(summary.get("stats"), dict)

    assert isinstance(markdown_report, str)
    assert f"# Static Rule Testing Report: {RULE_ID}" in markdown_report

    ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)
    summary_path = ARTIFACTS_DIR / f"pipeline_summary_{RULE_ID}.json"
    report_path = ARTIFACTS_DIR / f"pipeline_report_{RULE_ID}.md"

    summary_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    report_path.write_text(markdown_report, encoding="utf-8")

    assert summary_path.exists()
    assert report_path.exists()


@pytest.mark.integration
def test_pipeline_spotbugs_dmi_constant_password_generates_report():
    """Test SpotBugs analyzer with DMI_CONSTANT_DB_PASSWORD rule."""
    DATASET_DIR = WORKSPACE_ROOT / "dataset" / "spotbugs-security"
    ARTIFACTS_DIR = WORKSPACE_ROOT / "output"
    RULE_ID = "DMI_CONSTANT_DB_PASSWORD"
    
    if not os.getenv("DASHSCOPE_API_KEY"):
        pytest.skip("DASHSCOPE_API_KEY is required for the pipeline integration test")
    
    if not DATASET_DIR.exists():
        pytest.skip(f"SpotBugs dataset not found: {DATASET_DIR}")
    
    analyzer = SpotBugsAnalyzer(dataset_dir=str(DATASET_DIR))
    result = PipelineAgent(
        llm=llm,
        analyzer=analyzer,
        language="java",
    ).run(rule_id=RULE_ID)

    summary = result.get("pipeline_summary", {})
    markdown_report = result.get("markdown_report", "")

    assert summary, "Expected a non-empty pipeline summary"
    assert summary.get("rule_id") == RULE_ID
    assert summary.get("language") == "java"
    assert isinstance(summary.get("stats"), dict)

    assert isinstance(markdown_report, str)
    assert f"# Static Rule Testing Report: {RULE_ID}" in markdown_report

    ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)
    summary_path = ARTIFACTS_DIR / f"pipeline_summary_{RULE_ID}.json"
    report_path = ARTIFACTS_DIR / f"pipeline_report_{RULE_ID}.md"

    summary_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    report_path.write_text(markdown_report, encoding="utf-8")

    assert summary_path.exists()
    assert report_path.exists()


if __name__ == "__main__":
    # test_pipeline_bandit_b501_generates_report()
    # test_pipeline_semgrep_tainted_env_from_http_request_generates_report()
    # test_pipeline_codeql_generates_report()
    # test_pipeline_spotbugs_sql_injection_generates_report()
    # test_pipeline_spotbugs_dmi_constant_password_generates_report()
    pass