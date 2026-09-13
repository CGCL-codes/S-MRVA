#!/usr/bin/env python3
"""
Implementation for running CodeQL security checks on code files.

This module provides functionality to:
1. Run CodeQL checks on specific files with specific rule IDs
2. Parse and analyze CodeQL JSON output
3. Get detailed information about security issues found
"""

import json
import os
import re
import signal
import subprocess
import sys
from pathlib import Path
from typing import Dict, List, Optional, Any
import tempfile


def _run_with_timeout(cmd: List[str], timeout: int) -> subprocess.CompletedProcess:
    """Run a command, killing the WHOLE process tree on timeout.

    ``subprocess.run(timeout=...)`` only kills the direct child. The codeql
    CLI is a bash wrapper that spawns a JVM, so a timeout would orphan the
    java process (observed: 2h+ runaway JVMs consuming a core each). Running
    the child in its own session lets us SIGKILL the entire process group.
    """
    proc = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        start_new_session=True,
    )
    try:
        stdout, stderr = proc.communicate(timeout=timeout)
    except subprocess.TimeoutExpired:
        os.killpg(proc.pid, signal.SIGKILL)
        proc.wait()
        raise
    return subprocess.CompletedProcess(proc.args, proc.returncode, stdout, stderr)


class CodeQLCheckRunner:
    """Runner for CodeQL security checks on code files."""
    
    def __init__(self, language: str = "python"):
        """
        Initialize CodeQL runner.
        
        Args:
            language: Programming language
        """
        self.language = language
        self.codeql_cmd = "codeql"
    
    def run_codeql_check(
        self,
        file_path: str,
        rule_dir: str,
        rule_id: str,
    ) -> Dict[str, Any]:
        """
        Run CodeQL security check on a file.
        
        Args:
            file_path: Path to the file to check
            rule_dir: Path to the directory containing CodeQL rules
            rule_id: The rule ID
        
        Returns:
            Dictionary containing:
                - success: Boolean indicating if check ran successfully
                - output: Plain text output from CodeQL
                - issues_found: Boolean indicating if issues were detected
                - error: Error message if failed
        """
        try:
            file_path = Path(file_path)
            rule_dir = Path(rule_dir)
            
            # Find the .ql file in the rule directory
            ql_files = list(rule_dir.glob("*.ql"))
            print(ql_files)
            if not ql_files:
                return {
                    'success': False,
                    'error': f"No .ql file found in rule directory: {rule_dir}",
                    'issues_found': False,
                    'output': ''
                }
            
            query_file = str(ql_files[0].resolve())
            
            # Create a temporary directory for CodeQL database
            with tempfile.TemporaryDirectory() as temp_db_dir:
                db_path = Path(temp_db_dir) / f"{rule_id}_db"
                

                # Create CodeQL database from source
                create_db_cmd = [
                    self.codeql_cmd,
                    "database",
                    "create",
                    str(db_path),
                    "-l", self.language,
                    "-s", str(file_path.parent),
                ]
                
                create_result = _run_with_timeout(create_db_cmd, timeout=60)
                
                if create_result.returncode != 0 or not db_path.exists():
                    return {
                        'success': False,
                        'error': f"Failed to create CodeQL database: {create_result.stderr}",
                        'issues_found': False,
                        'output': create_result.stdout + "\n" + create_result.stderr
                    }
                
                # Create temporary files for BQRS and CSV output
                bqrs_file = Path(temp_db_dir) / f"{rule_id}_output.bqrs"
                csv_file = Path(temp_db_dir) / f"{rule_id}_output.csv"
                
                # Run CodeQL query on database, output to BQRS
                search_path = os.path.join(os.environ.get("SAT_WORK_DIR", "."), "data", "codeql")
                query_cmd = [
                    self.codeql_cmd,
                    "query",
                    "run",
                    str(query_file),
                    "-d", str(db_path),
                    "--search-path", search_path,
                    f"--output={str(bqrs_file)}"
                ]
                
                result = _run_with_timeout(query_cmd, timeout=120)
                
                if result.returncode != 0:
                    return {
                        'success': False,
                        'error': f"CodeQL query execution failed: {result.stderr}",
                        'issues_found': False,
                        'output': result.stdout + "\n" + result.stderr
                    }
                
                # Decode BQRS file to CSV
                decode_cmd = [
                    self.codeql_cmd,
                    "bqrs",
                    "decode",
                    "--format=csv",
                    f"--output={str(csv_file)}",
                    str(bqrs_file)
                ]
                
                decode_result = _run_with_timeout(decode_cmd, timeout=60)
                
                if decode_result.returncode != 0:
                    return {
                        'success': False,
                        'error': f"Failed to decode BQRS file: {decode_result.stderr}",
                        'issues_found': False,
                        'output': decode_result.stdout + "\n" + decode_result.stderr
                    }
                
                # Read the decoded CSV file
                full_output = ""
                issues_found = False
                
                try:
                    if csv_file.exists():
                        with open(csv_file, 'r') as f:
                            full_output = f.read()
                        
                        # Check if there are results (more than just the header line)
                        lines = full_output.strip().split('\n')
                        issues_found = len(lines) > 1
                    else:
                        return {
                            'success': False,
                            'error': f"Decoded CSV file not found: {csv_file}",
                            'issues_found': False,
                            'output': ''
                        }
                except IOError as e:
                    return {
                        'success': False,
                        'error': f"Error reading decoded CSV: {str(e)}",
                        'issues_found': False,
                        'output': ''
                    }
                
                return {
                    'success': True,
                    'output': full_output,
                    'issues_found': issues_found,
                    'file_path': str(file_path),
                    'query_file': str(query_file),
                    'exit_code': result.returncode
                }
            
        except FileNotFoundError:
            return {
                'success': False,
                'error': "CodeQL is not installed. Run: codeql --version or install from https://github.com/github/codeql",
                'issues_found': False,
                'output': ''
            }
        except subprocess.TimeoutExpired:
            return {
                'success': False,
                'error': "CodeQL execution timed out",
                'issues_found': False,
                'output': ''
            }
        except Exception as e:
            return {
                'success': False,
                'error': f"Failed to run CodeQL: {str(e)}",
                'issues_found': False,
                'output': ''
            }
    
    def format_results(self, result: Dict[str, Any], verbose: bool = False) -> str:
        """
        Format CodeQL check results into a human-readable string.
        
        Args:
            result: Result dictionary from run_codeql_check
            verbose: If True, include detailed information
        
        Returns:
            Formatted string representation of the results
        """
        if not result.get('success', False):
            error_msg = result.get('error', 'Unknown error')
            return f"Error: {error_msg}\n\nOutput:\n{result.get('output', '')}"
        
        output = result.get('output', '')
        
        # Add a header
        header = f"CodeQL Check Results for {result.get('file_path', 'N/A')}\n"
        header += "=" * 60 + "\n"
        
        if output:
            return header + output
        else:
            return header + "No issues found."
