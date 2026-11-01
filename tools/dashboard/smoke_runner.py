"""Run the kit smoke tests on demand (subprocess, repo root, bounded time)."""
import re
import subprocess
import sys

from editable_paths import repo

COMMAND = [sys.executable, "-m", "unittest", "discover", "-s", "evaluations/smoke", "-v"]


def run(timeout=180):
    try:
        proc = subprocess.run(COMMAND, cwd=repo(), capture_output=True, text=True, timeout=timeout)
    except subprocess.TimeoutExpired:
        return {"ok": False, "returncode": None, "ran": 0, "output": f"timed out after {timeout}s"}
    output = (proc.stdout or "") + (proc.stderr or "")
    m = re.search(r"Ran (\d+) tests?", output)
    return {"ok": proc.returncode == 0, "returncode": proc.returncode,
            "ran": int(m.group(1)) if m else 0, "output": output, "command": " ".join(COMMAND[1:])}
