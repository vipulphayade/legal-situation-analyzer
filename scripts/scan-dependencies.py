"""Lightweight dependency vulnerability scanner.

Usage:
    pip install pip-audit
    python scripts/scan-dependencies.py

Or run pip-audit directly:
    pip-audit -r api/requirements.txt
"""

import subprocess
import sys


def main() -> int:
    print("Dependency security scanner")
    print("=" * 50)
    print()

    try:
        import pip_audit  # noqa: F401
    except ImportError:
        print("pip-audit is not installed.")
        print("Install it with: pip install pip-audit")
        print()
        print("Then run: pip-audit -r api/requirements.txt")
        return 1

    result = subprocess.run(
        [sys.executable, "-m", "pip_audit", "-r", "api/requirements.txt"],
        capture_output=True,
        text=True,
    )
    print(result.stdout)
    if result.stderr:
        print(result.stderr)
    return result.returncode


if __name__ == "__main__":
    sys.exit(main())
