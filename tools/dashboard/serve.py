#!/usr/bin/env python3
"""BM Agent Kit maintainer dashboard — stdlib only, localhost only.

  python3 tools/dashboard/serve.py            -> http://127.0.0.1:8765
  python3 tools/dashboard/serve.py --port 9000

This is a maintainer tool outside the agent runtime; nothing under tools/ is loaded by the agent.
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from dashboard_server import make_server  # noqa: E402
from editable_paths import repo  # noqa: E402


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--port", type=int, default=8765)
    args = ap.parse_args(argv)
    server = make_server("127.0.0.1", args.port)
    print(f"BM Agent Kit dashboard: http://127.0.0.1:{args.port}  (repo: {repo()})  Ctrl+C to stop")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nstopped")
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
