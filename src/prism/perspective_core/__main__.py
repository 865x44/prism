"""Perspective Core v0 CLI entrypoint.

Usage: python -m prism.perspective_core [args]
"""

from __future__ import annotations

import sys

from .cli import main

if __name__ == "__main__":
    sys.exit(main())
