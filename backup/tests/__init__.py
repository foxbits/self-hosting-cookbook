"""Test package bootstrap.

The runtime package lives in ``src/`` so the service directory can also hold the
Dockerfile, catalog and docs without polluting the importable package.
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path

logging.disable(logging.CRITICAL)

SRC = Path(__file__).resolve().parents[1] / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))
