"""Resolve the source `toronto-election-results` dataset directory.

Never hardcode an absolute user path: derive it from this repo's location and allow
an env override so the pipeline is portable when it runs on other machines.
"""

import os
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
_DEFAULT_RESULTS_DIR = _ROOT / "data" / "upstream" / "results"


def results_dir() -> Path:
    """Root of the clean election-results dataset (override with TORONTO_ELECTION_RESULTS_DIR)."""
    return Path(os.environ.get("TORONTO_ELECTION_RESULTS_DIR", _DEFAULT_RESULTS_DIR))


def output_dir() -> Path:
    """Where production defeatability artifacts are staged for backend feeds."""
    return _ROOT / "data" / "processed" / "defeatability"
