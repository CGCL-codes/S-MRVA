"""Tests for Markdown code-fence stripping before SAST analysis."""

import sys
from pathlib import Path

SRC_DIR = Path(__file__).resolve().parents[1]
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from agents.utils import strip_code_fence  # noqa: E402


def test_strips_backtick_fence_with_language():
    code = "```java\nclass X { void f() {} }\n```"
    assert strip_code_fence(code) == "class X { void f() {} }"


def test_strips_tilde_fence():
    code = "~~~c\nint main(void) { return 0; }\n~~~"
    assert strip_code_fence(code) == "int main(void) { return 0; }"


def test_strips_fence_with_surrounding_whitespace():
    code = "\n\n```python\nprint('ok')\n```\n\n"
    assert strip_code_fence(code) == "print('ok')"


def test_plain_code_is_unchanged():
    code = "class X {\n    void f() {}\n}"
    assert strip_code_fence(code) == code


def test_internal_fence_is_preserved():
    code = '```java\nString fence = "```";\n```'
    assert strip_code_fence(code) == 'String fence = "```";'


def test_empty_input():
    assert strip_code_fence("") == ""
