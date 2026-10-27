#!/usr/bin/env python3
"""
Implementation for running Bandit security checks on Python files.

Bandit is intentionally run as a category-level analyzer: all rules are
enabled, and any Bandit finding counts. Rules in the same ``BX0X`` family are
closely related, so a mutant for one rule may legitimately be captured by a
sibling rule. Exact rule-id filtering is therefore not used here.

The JSON output is used only to distinguish a real scan from a failed or
skipped one. A syntax error, missing file, or internal Bandit error must not
look like a clean scan.
"""

import json
import subprocess
from pathlib import Path
from typing import Dict, Optional, Any


class BanditCheckRunner:
    """Runner for Bandit security checks on Python files."""

    def run_bandit_check(
        self,
        file_path: str,
        test_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Run Bandit on a file.

        Args:
            file_path: Path to the Python file to check.
            test_id: Accepted for API compatibility. Bandit findings are
                intentionally category-level, so this is not used to filter
                results.

        Returns:
            Dictionary containing:
                - success: whether the scan completed successfully
                - output: human-readable output
                - issues_found: whether any Bandit finding was produced
                - file_path, test_id, exit_code
                - error: failure reason when success is False
        """
        file_path = Path(file_path)

        cmd = ['bandit', '-r', str(file_path), '-f', 'json']

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                cwd=str(file_path.parent if file_path.is_file() else file_path),
            )
        except FileNotFoundError:
            return {
                'success': False,
                'error': "Bandit is not installed. Run: pip install bandit",
                'issues_found': False,
                'output': '',
                'file_path': str(file_path),
                'test_id': test_id,
                'exit_code': None,
            }
        except Exception as exc:
            return {
                'success': False,
                'error': f"Failed to run Bandit: {exc}",
                'issues_found': False,
                'output': '',
                'file_path': str(file_path),
                'test_id': test_id,
                'exit_code': None,
            }

        stdout = getattr(result, 'stdout', '') or ''
        stderr = getattr(result, 'stderr', '') or ''
        returncode = getattr(result, 'returncode', 0)
        if not isinstance(returncode, int):
            returncode = 0

        parsed = None
        parse_error = None
        if not stdout.strip():
            parse_error = "Bandit produced no JSON output"
        else:
            try:
                parsed = json.loads(stdout)
            except (json.JSONDecodeError, ValueError) as exc:
                parse_error = f"invalid JSON: {exc}"

        if parsed is not None and not isinstance(parsed, dict):
            parse_error = "Bandit JSON output was not an object"
            parsed = None

        raw_results = parsed.get('results', []) if isinstance(parsed, dict) else []
        if not isinstance(raw_results, list):
            raw_results = []

        errors = parsed.get('errors', []) if isinstance(parsed, dict) else []
        if not isinstance(errors, list):
            errors = [errors]

        # Category-level matching: any Bxxx finding counts. Do not filter by
        # test_id; sibling rules in the same family are intentionally accepted.
        results = [item for item in raw_results if isinstance(item, dict)]
        issues_found = bool(results)

        failure_reasons = []
        if not issues_found:
            if parse_error:
                failure_reasons.append(f"Failed to parse Bandit JSON output: {parse_error}")
            if errors:
                failure_reasons.append(
                    "Bandit reported errors: "
                    + "; ".join(
                        str(err.get('reason', err)) if isinstance(err, dict) else str(err)
                        for err in errors
                    )
                )
            if returncode not in (0, 1):
                failure_reasons.append(
                    f"Bandit exited with an unexpected return code: {returncode}"
                )

        success = issues_found or not failure_reasons

        output_parts = []
        if stderr.strip():
            output_parts.append("Bandit stderr:\n" + stderr.strip())
        if parse_error:
            output_parts.append(f"JSON parse error: {parse_error}")
        if errors:
            output_parts.append(
                "Bandit errors:\n" + json.dumps(errors, indent=2, default=str)
            )
        if results:
            output_parts.append(f"Findings ({len(results)}):")
            for item in results:
                output_parts.append(
                    f"- [{item.get('test_id', '?')}] "
                    f"{item.get('filename', '?')}:{item.get('line_number', '?')} "
                    f"({item.get('issue_severity', '?')}) "
                    f"{item.get('issue_text', '')}"
                )
        elif failure_reasons:
            output_parts.append(
                "No findings identified, but the scan was not successful."
            )
        else:
            output_parts.append("No issues identified.")

        if failure_reasons and stdout.strip():
            output_parts.append("Raw stdout:\n" + stdout.strip())

        response = {
            'success': success,
            'output': "\n".join(output_parts),
            'issues_found': issues_found,
            'file_path': str(file_path),
            'test_id': test_id,
            'exit_code': returncode,
        }
        if failure_reasons:
            response['error'] = "; ".join(failure_reasons)
        return response

    def format_results(self, result: Dict[str, Any], verbose: bool = False) -> str:
        """Format a Bandit runner result for the verification pipeline."""
        if not result.get('success', False):
            parts = [f"Error: {result.get('error', 'Unknown error')}"]
            if result.get('output'):
                parts.append("")
                parts.append(str(result.get('output')))
            return "\n".join(parts)

        output = result.get('output', '')
        header = f"Bandit Check Results for {result.get('file_path', 'N/A')}\n"
        header += "=" * 60 + "\n"
        return header + output if verbose else output
