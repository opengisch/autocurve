"""
This script should be used to wrap calls to QGIS. It will check the output and set exit code
accordingly to test results, working around the issue about QGIS crashing on exitting from python.
"""

import subprocess
import sys

args = sys.argv[1:]

print(f"Running `{' '.join(args)}`...")

process = subprocess.run(args, capture_output=True, encoding="utf-8")

print(process.stdout)

if "__TESTS_SUCCESSFUL__" in process.stdout:
    sys.exit(0)
else:
    sys.exit(1)
