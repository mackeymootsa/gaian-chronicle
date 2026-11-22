#!/usr/bin/env python3
"""Run the same offline validation used before a release is activated."""

from pathlib import Path
import sys
import tempfile

from deploy import Deployment, clean_env


if __name__ == "__main__":
    root = Path(__file__).resolve().parents[1]
    try:
        with tempfile.TemporaryDirectory(prefix="gaian-verify-") as temporary:
            Deployment(Path(temporary) / "unused").validate(root, clean_env(temporary))
        print("Offline validation passed: Python compilation, JSON, shell syntax, and all tests")
    except Exception as error:
        print(f"Validation failed: {error}", file=sys.stderr)
        sys.exit(1)
