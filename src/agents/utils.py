"""Utility functions for agents."""

import json
import os
import re
from typing import Dict, Any


def env_int(name: str, default: int) -> int:
    """Read an integer from the environment, falling back to *default*.

    Returns *default* when the variable is unset, empty, or not a valid int,
    so a malformed value never crashes the pipeline.
    """
    raw = os.getenv(name)
    if raw is None or not raw.strip():
        return default
    try:
        return int(raw.strip())
    except ValueError:
        return default


def parse_json(response: str) -> Dict[str, Any]:
    """Parse JSON from LLM response.
    
    Attempts to extract JSON from markdown code blocks or raw JSON strings.
    
    Args:
        response: String response from LLM that may contain JSON
        
    Returns:
        Parsed JSON dictionary, or empty dict if parsing fails
    """
    # Try to find JSON in markdown code block
    json_match = re.search(r'```json\s*(.*?)\s*```', response, re.DOTALL)
    if json_match:
        try:
            return json.loads(json_match.group(1))
        except json.JSONDecodeError:
            pass
    
    # Try to find raw JSON object
    json_match = re.search(r'\{[\s\S]*\}', response)
    if json_match:
        try:
            return json.loads(json_match.group())
        except json.JSONDecodeError:
            pass
    
    return {}


if __name__ == "__main__":
    # Example usage
    response = """```json\n{\n  \"has_issue\": true,\n  \"reason\": \"The code uses ProcessBuilder which is functionally equivalent to Runtime.exec for subprocess execution. User-supplied input from the HTTP header is directly injected into the process environment map via env.put(), allowing an attacker to manipulate environment variables passed to the OS command, constituting the same command injection vulnerability.\"\n}\n```"""
    parsed = parse_json(response)
    print(parsed)
