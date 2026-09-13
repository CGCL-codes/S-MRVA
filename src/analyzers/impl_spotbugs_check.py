#!/usr/bin/env python3
"""
Implementation for running SpotBugs security checks on Java code files.

This module provides functionality to:
1. Compile Java source files to bytecode
2. Run SpotBugs analysis on compiled classes
3. Parse and analyze SpotBugs XML output
4. Get detailed information about security issues found
"""

import json
import os
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Dict, List, Any


class SpotBugsCheckRunner:
    """Runner for SpotBugs security checks on Java code files."""
    
    def __init__(self):
        """Initialize SpotBugs runner."""
        self.spotbugs_cmd = "spotbugs"
        self.javac_cmd = "javac"
        self.classpath = self._build_classpath()
    
    def _build_classpath(self) -> str:
        """
        Build classpath by finding and joining all SpotBugs dependencies and compiled test classes.
        
        Returns:
            Classpath string with all JAR files and test classes separated by OS-specific separator
        """
        import platform
        path_separator = ";" if platform.system() == "Windows" else ":"
        
        classpath_items = []
        work_dir = Path(os.getenv("SAT_WORK_DIR", "."))
        
        # 1. Add JAR files from workspace root _libs directory
        libs_dir = work_dir / "_libs"
        if libs_dir.exists():
            jar_files = sorted(libs_dir.glob("*.jar"))
            classpath_items.extend(jar_files)
        
        # 2. Add compiled test classes from dataset-specific _libs directory
        # This includes the pre-compiled SpotBugs test case classes
        dataset_libs_dir = work_dir / "dataset" / "spotbugs-security" / "_libs"
        if dataset_libs_dir.exists():
            # Add the main compiled classes directories
            java_classes = dataset_libs_dir / "java" / "main"
            groovy_classes = dataset_libs_dir / "groovy" / "main"
            
            if java_classes.exists():
                classpath_items.append(java_classes)
            if groovy_classes.exists():
                classpath_items.append(groovy_classes)
        
        # Also add JAR files from dataset _libs (some may be duplicates, but harmless)
        if dataset_libs_dir.exists():
            dataset_jars = sorted(dataset_libs_dir.glob("*.jar"))
            classpath_items.extend(dataset_jars)
        
        if classpath_items:
            classpath = path_separator.join(str(f) for f in classpath_items)
            return classpath
        
        # Fallback: try to find SpotBugs installation libs
        try:
            result = subprocess.run(
                ["which", "spotbugs"],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode == 0:
                spotbugs_home = Path(result.stdout.strip()).parent.parent
                spotbugs_libs = spotbugs_home / "lib"
                if spotbugs_libs.exists():
                    jar_files = sorted(spotbugs_libs.glob("*.jar"))
                    if jar_files:
                        classpath = path_separator.join(str(f) for f in jar_files)
                        return classpath
        except:
            pass
        
        # Return empty classpath if nothing found
        return ""
    
    def _compile_java_file(self, file_path: str, output_dir: str) -> bool:
        """
        Compile a Java source file to bytecode with SpotBugs dependencies.
        
        Args:
            file_path: Path to the Java source file
            output_dir: Directory to output compiled .class files
        
        Returns:
            Boolean indicating success
        """
        try:
            # Always compile the provided source to keep findings aligned with current code.
            cmd = [
                self.javac_cmd,
                "-d", output_dir,
                "-proc:none",  # Disable annotation processing
                "-Xlint:-options"  # Suppress javac option warnings
            ]
            
            # Add classpath if available
            if self.classpath:
                cmd.extend(["-cp", self.classpath])
            
            cmd.append(file_path)
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=30,
                shell=False
            )
            
            if result.returncode != 0:
                # Log compilation error for debugging
                print(f"Javac error output: {result.stderr}")
                
                # Try alternative: add -XDignoreSourceErrors for lenient compilation
                cmd_lenient = cmd + ["-XDignoreSourceErrors"]
                result = subprocess.run(
                    cmd_lenient,
                    capture_output=True,
                    text=True,
                    timeout=30,
                    shell=False
                )
            
            return result.returncode == 0
        except Exception as e:
            print(f"Error compiling Java file: {e}")
            return False
    
    def run_spotbugs_check(
        self,
        file_path: str,
        rule_id: str,
    ) -> Dict[str, Any]:
        """
        Run SpotBugs security check on a Java file.
        
        Args:
            file_path: Path to the Java source file to check
            rule_id: The SpotBugs bug type ID (e.g., "SQL_NONCONSTANT_STRING_PASSED_TO_EXECUTE")
        
        Returns:
            Dictionary containing:
                - success: Boolean indicating if check ran successfully
                - output: Plain text output from SpotBugs
                - issues_found: Boolean indicating if issues of the specific type were detected
                - error: Error message if failed
                - bug_count: Number of bugs of this type found
        """
        try:
            file_path = Path(file_path)
            
            if not file_path.exists():
                return {
                    'success': False,
                    'error': f"File not found: {file_path}",
                    'issues_found': False,
                    'output': '',
                    'bug_count': 0
                }
            
            # Create temporary directory for compilation
            with tempfile.TemporaryDirectory() as temp_dir:
                temp_dir_path = Path(temp_dir)
                class_output_dir = temp_dir_path / "classes"
                class_output_dir.mkdir()
                
                # Compile Java file
                compile_success = self._compile_java_file(
                    str(file_path),
                    str(class_output_dir),
                )
                if not compile_success:
                    return {
                        'success': False,
                        'error': f"Failed to compile Java file: {file_path}",
                        'issues_found': False,
                        'output': '',
                        'bug_count': 0
                    }
                
                # Run SpotBugs analysis
                output_file = temp_dir_path / "spotbugs_output.xml"
                
                cmd = [
                    self.spotbugs_cmd,
                    "-longBugCodes",
                    "-low",
                    "-xml:withMessages",
                    # "-bugCategories", "SECURITY",
                    "-output", str(output_file),
                    str(class_output_dir)
                ]
                
                result = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    timeout=60
                )
                
                # SpotBugs returns non-zero even when successful but issues found
                if result.returncode not in (0, 1):
                    return {
                        'success': False,
                        'error': f"SpotBugs command failed: {result.stderr}",
                        'issues_found': False,
                        'output': result.stderr,
                        'bug_count': 0
                    }
                
                # Parse XML output
                issues_found = False
                bug_count = 0
                bug_details = []
                
                if output_file.exists():
                    try:
                        tree = ET.parse(output_file)
                        root = tree.getroot()
                        
                        # Look for BugInstance elements matching the rule_id
                        for bug_instance in root.findall(".//BugInstance"):
                            bug_type = bug_instance.get("type", "")
                            if bug_type == rule_id:
                                issues_found = True
                                bug_count += 1
                                
                                # Extract bug details
                                priority = bug_instance.get("priority", "")
                                abbrev = bug_instance.get("abbrev", "")
                                
                                # Get source line information
                                source_line = bug_instance.find(".//SourceLine")
                                if source_line is not None:
                                    start_line = source_line.get("start", "")
                                    end_line = source_line.get("end", "")
                                    bug_details.append({
                                        'type': bug_type,
                                        'priority': priority,
                                        'abbrev': abbrev,
                                        'line': f"{start_line}-{end_line}" if start_line and end_line else start_line or "unknown"
                                    })
                    except Exception as e:
                        print(f"Error parsing SpotBugs XML: {e}")
                
                # Format output
                output = f"SpotBugs Check Results for {rule_id}\n"
                output += "=" * 60 + "\n"
                output += f"File: {file_path}\n"
                output += f"Issues Found: {issues_found}\n"
                output += f"Bug Count: {bug_count}\n"
                
                if bug_details:
                    output += "\nBug Details:\n"
                    for bug in bug_details:
                        output += f"  - {bug['type']} (Priority: {bug['priority']}, Line: {bug['line']})\n"
                
                if result.stdout:
                    output += f"\nSpotBugs Output:\n{result.stdout}\n"
                
                return {
                    'success': True,
                    'output': output,
                    'issues_found': issues_found,
                    'bug_count': bug_count,
                    'bug_details': bug_details
                }
                
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'issues_found': False,
                'output': '',
                'bug_count': 0
            }
    
    def format_results(self, result: Dict[str, Any], verbose: bool = False) -> str:
        """
        Format the results of a SpotBugs check into a human-readable string.
        
        Args:
            result: Dictionary returned from run_spotbugs_check
            verbose: Whether to include verbose output
        
        Returns:
            Formatted result string
        """
        output = ""
        
        if not result.get('success', False):
            output += f"ERROR: {result.get('error', 'Unknown error')}\n"
        else:
            if verbose:
                output += result.get('output', '')
            else:
                # Compact format
                output += f"Issues Found: {result.get('issues_found', False)}\n"
                output += f"Bug Count: {result.get('bug_count', 0)}\n"
                if result.get('bug_details'):
                    output += "Bugs:\n"
                    for bug in result.get('bug_details', []):
                        output += f"  {bug['type']} at line {bug['line']}\n"
        
        return output
