"""Path guards for Kit scripts (review finding: allowlisted scripts must not read/write outside their lane)."""
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
RUNS = REPO / "runs"


def _resolve(path):
    return Path(path).expanduser().resolve()


def require_inside_repo(path):
    """Input files must live inside the repository (prevents dumping ~/.aws/credentials via `kit-cli scan`)."""
    p = _resolve(path)
    if not p.is_relative_to(REPO):
        raise PermissionError(f"refusing path outside repository: {path}")
    return p


def require_inside_runs(path):
    """Output files may only be written under runs/ and never as executable code."""
    p = _resolve(path)
    if not p.is_relative_to(RUNS):
        raise PermissionError(f"refusing to write outside runs/: {path}")
    if p.suffix.lower() in {".py", ".sh", ".js", ".ts", ".rb", ".pl", ".command"}:
        raise PermissionError(f"refusing to write executable file under runs/: {path}")
    return p


def repo_relative(path):
    p = _resolve(path)
    return str(p.relative_to(REPO)) if p.is_relative_to(REPO) else str(p)
