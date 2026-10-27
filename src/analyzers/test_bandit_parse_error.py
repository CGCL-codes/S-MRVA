"""Regression tests for Bandit parse-error detection.

Bandit findings remain category-level: any Bxxx finding counts, even if it comes
from a sibling rule. What changes here is that a skipped or unparsable file is
no longer treated as a clean scan.
"""

import os
from pathlib import Path

from impl_bandit_check import BanditCheckRunner


def test_bandit_syntax_error_is_not_a_clean_scan(tmp_path):
    target = tmp_path / "broken.py"
    target.write_text("def broken(:\n    pass\n")

    result = BanditCheckRunner().run_bandit_check(str(target), test_id="B105")
    assert result["success"] is False
    assert result["issues_found"] is False
    assert result.get("error")
    assert "syntax" in result["error"].lower() or "parse" in result["error"].lower()


def test_bandit_missing_file_is_not_a_clean_scan(tmp_path):
    missing = tmp_path / "does-not-exist.py"

    result = BanditCheckRunner().run_bandit_check(str(missing), test_id="B105")
    assert result["success"] is False
    assert result["issues_found"] is False
    assert result.get("error")


def test_bandit_findings_remain_category_level(tmp_path):
    """A sibling-rule finding still counts; no exact rule-id filtering."""
    target = tmp_path / "binding.py"
    target.write_text(
        "import socket\n"
        "s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)\n"
        "s.bind(('0.0.0.0', 31137))\n"
    )

    result = BanditCheckRunner().run_bandit_check(str(target), test_id="B105")
    assert result["success"] is True
    assert result["issues_found"] is True
    assert "B104" in result["output"]
