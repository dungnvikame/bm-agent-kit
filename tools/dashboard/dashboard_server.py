"""HTTP layer for the maintainer dashboard: localhost-only JSON API + one static page.

GET  /                      static/index.html
GET  /static/<name>         static assets (flat directory, no traversal)
GET  /api/overview|skills|policies|product|evaluations|plans|files
GET  /api/file?path=<rel>   editable or read-only canonical file
POST /api/file              {"path": rel, "text": str}      guarded save (repo_writer)
POST /api/contract          {"path": rel, "json": object}   guarded JSON save
POST /api/evaluations/run   run the smoke tests
Every /api request must carry a loopback Host (and Origin on POST) to block cross-site calls.
"""
import json
import mimetypes
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

import repo_reader
import repo_writer
import smoke_runner
from editable_paths import viewable_files
from repo_writer import SaveRefused

STATIC_DIR = Path(__file__).resolve().parent / "static"
LOOPBACK_HOSTS = ("127.0.0.1", "localhost", "[::1]")
GET_VIEWS = {
    "/api/overview": repo_reader.layers_view, "/api/skills": repo_reader.skills_view,
    "/api/policies": repo_reader.policies_view, "/api/product": repo_reader.product_view,
    "/api/evaluations": repo_reader.evaluations_view, "/api/plans": repo_reader.plans_view,
    "/api/files": viewable_files,
}


def _host_ok(value):
    host = (value or "").split(":")[0] if not (value or "").startswith("[") else value.split("]")[0] + "]"
    return host in LOOPBACK_HOSTS


class DashboardHandler(BaseHTTPRequestHandler):
    server_version = "BMKitDashboard/0.1"

    def log_message(self, fmt, *args):  # quieter console
        print("%s %s" % (self.command, fmt % args))

    # ---- helpers -------------------------------------------------------
    def _send_json(self, payload, status=200):
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def _send_static(self, name):
        path = STATIC_DIR / name
        if "/" in name or ".." in name or not path.is_file() or path.parent != STATIC_DIR:
            return self._send_json({"error": "not found"}, 404)
        body = path.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", mimetypes.guess_type(name)[0] or "application/octet-stream")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def _guard(self, post=False):
        if not _host_ok(self.headers.get("Host")):
            self._send_json({"error": "forbidden host"}, 403)
            return False
        origin = self.headers.get("Origin")
        if post and origin and not _host_ok(urlsplit(origin).netloc):
            self._send_json({"error": "forbidden origin"}, 403)
            return False
        return True

    def _read_body(self):
        length = int(self.headers.get("Content-Length") or 0)
        if length > 2_000_000:
            raise ValueError("body too large")
        data = json.loads(self.rfile.read(length).decode("utf-8") or "{}")
        if not isinstance(data, dict):
            raise ValueError("body must be a JSON object")
        return data

    def _run(self, fn, *args):
        try:
            return self._send_json(fn(*args))
        except SaveRefused as exc:
            return self._send_json({"error": str(exc), "violations": exc.details}, 409)
        except PermissionError as exc:
            return self._send_json({"error": str(exc)}, 403)
        except FileNotFoundError as exc:
            return self._send_json({"error": f"not found: {exc}"}, 404)
        except (ValueError, KeyError, TypeError) as exc:
            return self._send_json({"error": str(exc)}, 400)

    # ---- routes --------------------------------------------------------
    def do_GET(self):
        url = urlsplit(self.path)
        if url.path == "/":
            return self._send_static("index.html")
        if url.path.startswith("/static/"):
            return self._send_static(url.path[len("/static/"):])
        if not url.path.startswith("/api/") or not self._guard():
            return None if url.path.startswith("/api/") else self._send_json({"error": "not found"}, 404)
        if url.path in GET_VIEWS:
            return self._run(GET_VIEWS[url.path])
        if url.path == "/api/file":
            rel = parse_qs(url.query).get("path", [""])[0]
            return self._run(repo_reader.file_view, rel)
        return self._send_json({"error": "not found"}, 404)

    def do_POST(self):
        url = urlsplit(self.path)
        if not url.path.startswith("/api/") or not self._guard(post=True):
            return None if url.path.startswith("/api/") else self._send_json({"error": "not found"}, 404)
        try:
            body = self._read_body() if url.path != "/api/evaluations/run" else {}
        except ValueError as exc:
            return self._send_json({"error": str(exc)}, 400)
        if url.path == "/api/file":
            return self._run(repo_writer.save_text, body.get("path"), body.get("text"))
        if url.path == "/api/contract":
            return self._run(repo_writer.save_json, body.get("path"), body.get("json"))
        if url.path == "/api/evaluations/run":
            return self._run(smoke_runner.run)
        return self._send_json({"error": "not found"}, 404)


def make_server(host="127.0.0.1", port=8765):
    if host not in LOOPBACK_HOSTS:
        raise ValueError("dashboard binds to loopback only")
    return ThreadingHTTPServer((host, port), DashboardHandler)
