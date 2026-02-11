"""Diagnostic utility: scan WhiteboxTools installation.

Locates the WhiteboxTools binary and lists available tools matching
specified keywords. Useful for resolving version discrepancies where
tool names may differ (e.g., 'LinesToPoints' vs 'ExtractNodes').

Usage:
    python check_whitebox.py
    python check_whitebox.py --keywords Slope TRI Aspect
"""

import os
import sys
import argparse
import subprocess
import logging

import whitebox

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

DEFAULT_KEYWORDS = ["Vertices", "Points", "Nodes", "Convert", "Slope", "TRI"]


def find_whitebox_binary() -> str:
    """Locate the WhiteboxTools executable."""
    module_dir = os.path.dirname(whitebox.__file__)
    candidates = [
        os.path.join(module_dir, "WBT", "whitebox_tools"),
        os.path.join(module_dir, "whitebox_tools"),
    ]
    for path in candidates:
        if os.path.exists(path):
            if sys.platform != "win32":
                try:
                    os.chmod(path, 0o755)
                except OSError:
                    pass
            return path
    return whitebox.WhiteboxTools().exe_path


def list_tools(executable: str, keywords: list[str]) -> None:
    """Search installed WhiteboxTools for matching tool names."""
    for keyword in keywords:
        logger.info("Searching tools matching '%s' ...", keyword)
        try:
            subprocess.run([executable, "--listtools", keyword], check=False)
        except OSError as exc:
            logger.error("Failed to query tools: %s", exc)


def main():
    parser = argparse.ArgumentParser(description="Scan WhiteboxTools installation.")
    parser.add_argument("--keywords", nargs="+", default=DEFAULT_KEYWORDS,
                        help="Keywords to search for in tool names.")
    args = parser.parse_args()

    executable = find_whitebox_binary()
    logger.info("WhiteboxTools binary: %s", executable)
    list_tools(executable, args.keywords)


if __name__ == "__main__":
    main()