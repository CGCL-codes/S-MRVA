"""Shared pytest setup.

The analyzer modules resolve their dataset paths from ``SAT_WORK_DIR`` at
import time (``src/analyzers/semgrep_check.py`` raises if it is unset).  Setting
it here makes ``pytest`` work from a fresh checkout without every caller having
to remember ``SAT_WORK_DIR=$PWD pytest ...``.
"""

import os
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent
os.environ.setdefault("SAT_WORK_DIR", str(REPO_ROOT))
