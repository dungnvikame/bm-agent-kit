"""HTTP layer: routes, loopback guard, error mapping. Runs a real server on an ephemeral port."""
import json
import threading
import unittest
import urllib.error
import urllib.request

import repo_fixture  # noqa: F401
import dashboard_server


class DashboardServerTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp, cls.cleanup = repo_fixture.make_temp_repo()
        cls.server = dashboard_server.make_server("127.0.0.1", 0)
        cls.port = cls.server.server_address[1]
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.cleanup()

    def call(self, path, body=None, headers=None):
        data = json.dumps(body).encode() if body is not None else None
        req = urllib.request.Request(f"http://127.0.0.1:{self.port}{path}", data=data, method="POST" if data else "GET")
        req.add_header("Content-Type", "application/json")
        for k, v in (headers or {}).items():
            req.add_header(k, v)
        try:
            with urllib.request.urlopen(req, timeout=10) as res:
                return res.status, res.headers.get("Content-Type", ""), res.read()
        except urllib.error.HTTPError as exc:
            return exc.code, exc.headers.get("Content-Type", ""), exc.read()

    def test_static_page_and_assets(self):
        status, ctype, body = self.call("/")
        self.assertEqual(status, 200)
        self.assertIn("text/html", ctype)
        self.assertIn(b"Maintainer Dashboard", body)
        self.assertEqual(self.call("/static/dashboard-core.js")[0], 200)
        self.assertEqual(self.call("/static/../serve.py")[0], 404)
        self.assertEqual(self.call("/static/%2e%2e/serve.py")[0], 404)

    def test_read_endpoints(self):
        for path in ("/api/overview", "/api/skills", "/api/policies", "/api/product", "/api/evaluations", "/api/plans", "/api/files"):
            status, _, body = self.call(path)
            self.assertEqual(status, 200, path)
            json.loads(body)
        status, _, body = self.call("/api/file?path=core/contracts/core-contract.json")
        self.assertEqual(json.loads(body)["kind"], "read_only")

    def test_private_and_unknown_paths(self):
        self.assertEqual(self.call("/api/file?path=runs/secret-run/intake.json")[0], 403)
        self.assertEqual(self.call("/api/file?path=products/igoal/source-registry.local.json")[0], 403)
        self.assertEqual(self.call("/api/file?path=core/policies/nope.md")[0], 404)
        self.assertEqual(self.call("/api/nope")[0], 404)

    def test_refused_contract_save_returns_violations(self):
        _, _, body = self.call("/api/file?path=roles/pm/pm-role-contract.json")
        role = json.loads(json.loads(body)["text"])
        role["tools"]["sends"] = "enabled"
        status, _, body = self.call("/api/contract", {"path": "roles/pm/pm-role-contract.json", "json": role})
        self.assertEqual(status, 409)
        self.assertTrue(any("tools.sends is locked" in v for v in json.loads(body)["violations"]))

    def test_generated_copy_save_forbidden_and_bad_body(self):
        self.assertEqual(self.call("/api/file", {"path": "AGENTS.md", "text": "x"})[0], 403)
        self.assertEqual(self.call("/api/file", {"path": "roles/pm/pm-role-contract.json", "text": "{bad"})[0], 409)
        self.assertEqual(self.call("/api/contract", {"path": "roles/pm/pm-role-contract.json", "json": [1]})[0], 409)

    def test_cross_site_guard(self):
        self.assertEqual(self.call("/api/overview", headers={"Host": "evil.example"})[0], 403)
        status, _, _ = self.call("/api/file", {"path": "core/policies/safety-policy.md", "text": "x"}, headers={"Origin": "http://evil.example"})
        self.assertEqual(status, 403)
        self.assertEqual(self.call("/api/overview", headers={"Origin": "http://127.0.0.1:1"})[0], 200)

    def test_non_loopback_bind_refused(self):
        with self.assertRaises(ValueError):
            dashboard_server.make_server("0.0.0.0", 0)


if __name__ == "__main__":
    unittest.main()
