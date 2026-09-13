#!/usr/bin/env python3
"""
Implementation for running Bandit security checks on Python files.

This module provides functionality to:
1. Run Bandit checks on specific files with specific test IDs
2. List available Bandit rules
3. Parse and analyze Bandit JSON output
4. Get detailed information about security issues found
"""

import json
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Dict, Optional, Any


class BanditCheckRunner:
    """Runner for Bandit security checks on Python files."""
    
    def run_bandit_check(
        self, 
        file_path: str, 
        test_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Run Bandit security check on a file.
        
        Args:
            file_path: Path to the Python file to check
            test_id: Specific test ID to run (e.g., 'B506'). If None, runs all tests.
        
        Returns:
            Dictionary containing:
                - success: Boolean indicating if check ran successfully
                - output: Plain text output from Bandit
                - issues_found: Boolean indicating if issues were detected
                - error: Error message if failed
        """
        file_path = Path(file_path)
        
        # Build Bandit command (without -f json for plain text output)
        cmd = ['bandit', '-r', str(file_path)]
        
        # use all rules. 
        # if test_id:
        #     cmd.extend(['-t', test_id])
        
        try:
            # Run Bandit (note: exit code 1 means issues found, which is not an error)
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                cwd=str(file_path.parent if file_path.is_file() else file_path)
            )
            
            # Combine stdout and stderr for full output
            full_output = result.stdout
            if result.stderr:
                full_output += "\n" + result.stderr
            
            # Use regex to detect if issues were found
            # Bandit outputs "No issues identified." when clean
            # Or shows issue count like ">> Issue: [B506:yaml_load]"
            issues_found = False
            if full_output:
                # Check for "No issues identified"
                if "No issues identified" not in full_output:
                    # Check for issue patterns
                    issue_pattern = re.compile(r'>>\s+Issue:\s+\[([A-Z]\d+):', re.MULTILINE)
                    if issue_pattern.search(full_output):
                        issues_found = True
            
            return {
                'success': True,
                'output': full_output,
                'issues_found': issues_found,
                'file_path': str(file_path),
                'test_id': test_id,
                'exit_code': result.returncode
            }
            
        except FileNotFoundError:
            return {
                'success': False,
                'error': "Bandit is not installed. Run: pip install bandit",
                'issues_found': False,
                'output': ''
            }
        except Exception as e:
            return {
                'success': False,
                'error': f"Failed to run Bandit: {str(e)}",
                'issues_found': False,
                'output': ''
            }
    
    def format_results(self, result: Dict[str, Any], verbose: bool = False) -> str:
        """
        Format Bandit check results into a human-readable string.
        
        Args:
            result: Result dictionary from run_bandit_check
            verbose: If True, include detailed information (currently unused as we return raw output)
        
        Returns:
            Formatted string representation of the results
        """
        if not result.get('success', False):
            return f"Error: {result.get('error', 'Unknown error')}"
        
        # Return the raw output from Bandit (it's already well-formatted)
        output = result.get('output', '')
        
        # Add a header
        header = f"Bandit Check Results for {result.get('file_path', 'N/A')}\n"
        header += "=" * 60 + "\n"
        
        if verbose:
            return header + output
        else:
            # For non-verbose, just return the output
            return output