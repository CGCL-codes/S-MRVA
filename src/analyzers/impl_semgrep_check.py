#!/usr/bin/env python3
"""
Implementation for running Semgrep security checks on code files.

This module provides functionality to:
1. Run Semgrep checks on specific files with specific rule IDs
2. List available Semgrep rules
3. Parse and analyze Semgrep JSON output
4. Get detailed information about security issues found
"""

import json
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Dict, List, Optional, Any


class SemgrepCheckRunner:
    """Runner for Semgrep security checks on code files."""
    
    def run_semgrep_check(
        self, 
        file_path: str,
        rule_path: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Run Semgrep security check on a file.
        
        Args:
            file_path: Path to the file to check
            rule_path: Path to the Semgrep rule YAML file to use
        
        Returns:
            Dictionary containing:
                - success: Boolean indicating if check ran successfully
                - output: Plain text output from Semgrep
                - issues_found: Boolean indicating if issues were detected
                - error: Error message if failed
        """
            
        # Build Semgrep command (without --json for plain text output)
        # Add no autofix to prevent any changes to the code
        cmd = ['semgrep', '--no-autofix', '--config', str(rule_path), str(file_path)]
        # cmd = ['semgrep', '--config', "auto", str(file_path)]
        
        try:
            env = os.environ.copy()
            for v in ('HTTP_PROXY', 'HTTPS_PROXY', 'http_proxy', 'https_proxy'):
                env.pop(v, None)
            
            # Run Semgrep
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                env=env,
            )
            
            # Combine stdout and stderr for full output
            full_output = result.stdout
            if result.stderr:
                full_output += "\n" + result.stderr
            
            # Use regex to detect if issues were found
            # Semgrep shows findings in the format:
            # "  ┌─► <filename>:<line>:<column>"
            # Or summary like "ran 1 rule on 1 file: X findings"
            issues_found = False
            if full_output:
                # Check for findings in summary
                findings_pattern = re.compile(r'(\d+)\s+findings?', re.IGNORECASE)
                match = findings_pattern.search(full_output)
                if match:
                    num_findings = int(match.group(1))
                    issues_found = num_findings > 0
                
                # Also check for the finding marker
                if not issues_found:
                    finding_marker = re.compile(r'┌─►|└─►', re.MULTILINE)
                    if finding_marker.search(full_output):
                        issues_found = True
            
            return {
                'success': True,
                'output': full_output,
                'issues_found': issues_found,
                'file_path': str(file_path),
                'rule_path': str(rule_path),
                'exit_code': result.returncode
            }
            
        except FileNotFoundError:
            return {
                'success': False,
                'error': "Semgrep is not installed. Run: pip install semgrep",
                'issues_found': False,
                'output': ''
            }
        except Exception as e:
            return {
                'success': False,
                'error': f"Failed to run Semgrep: {str(e)}",
                'issues_found': False,
                'output': ''
            }
    
    def format_results(self, result: Dict[str, Any], verbose: bool = False) -> str:
        """
        Format Semgrep check results into a human-readable string.
        
        Args:
            result: Result dictionary from run_semgrep_check
            verbose: If True, include detailed information (currently unused as we return raw output)
        
        Returns:
            Formatted string representation of the results
        """
        if not result.get('success', False):
            return f"Error: {result.get('error', 'Unknown error')}"
        
        # Return the raw output from Semgrep (it's already well-formatted)
        output = result.get('output', '')
        
        # Add a header
        header = f"Semgrep Check Results for {result.get('file_path', 'N/A')}\n"
        header += "=" * 60 + "\n"
        
        if verbose:
            return header + output
        else:
            # For non-verbose, just return the output
            return output