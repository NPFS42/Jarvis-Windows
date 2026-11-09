import sys
from pathlib import Path
from unittest.mock import patch
import unittest
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import jarvis_frontend as app

class FrontendTests(unittest.TestCase):
    def test_tailscale_addresses_only(self):
        for addr in ("100.64.0.1", "100.93.225.62", "100.127.255.254", "fd7a:115c:a1e0::1"):
            self.assertTrue(app.is_tailscale_address(addr), addr)
        for addr in ("100.63.255.255", "100.128.0.1", "192.168.0.1", "8.8.8.8", "::1"):
            self.assertFalse(app.is_tailscale_address(addr), addr)

    def test_valid_hosts(self):
        self.assertTrue(app.valid_tailnet_host("home.tail-abc.ts.net"))
        for host in ("google.com", "localhost", "100.93.225.62",
                     "home.tail-abc.ts.net.evil.com", "bad host.tail.ts.net"):
            self.assertFalse(app.valid_tailnet_host(host), host)

    def test_local_navigation_policy(self):
        for target in ("http://127.0.0.1:8765/", "http://127.0.0.1:8765/api/state"):
            self.assertTrue(app.allowed_navigation(target, app.LOCAL), target)
        for target in ("http://localhost:8765/", "file:///c:/private",
                       "http://127.0.0.1:8766/", "https://example.com/"):
            self.assertFalse(app.allowed_navigation(target, app.LOCAL), target)

    def test_remote_navigation_policy(self):
        target = "https://home.tail-abc.ts.net/"
        self.assertTrue(app.allowed_navigation(target+"api/state", target))
        for bad in ("http://home.tail-abc.ts.net/", "https://google.com/",
                    "https://home.tail-abc.ts.net:8443/", "file:///secret",
                    "https://name@home.tail-abc.ts.net/"):
            self.assertFalse(app.allowed_navigation(bad, target), bad)

    def test_existing_local_service_selected_first(self):
        with patch.object(app, "local_status", return_value="ready"), \
             patch.object(app, "message_box") as confirm, \
             patch.object(app, "owner_peers") as peers:
            self.assertEqual(app.choose_backend(), app.LOCAL)
            confirm.assert_not_called()
            peers.assert_not_called()

    def test_declined_local_start_selects_tailnet(self):
        with patch.object(app, "local_status", return_value="stopped"), \
             patch.object(app, "message_box", side_effect=[False, True, True]), \
             patch.object(app, "owner_peers", return_value=[
                 {"name": "Home", "host": "home.tail-abc.ts.net"}]), \
             patch.object(app, "probe_host", return_value=True):
            self.assertEqual(app.choose_backend(), "https://home.tail-abc.ts.net/")

    def test_no_private_backend_code_imported(self):
        import ast
        tree = ast.parse(Path(app.__file__).read_text(encoding="utf-8"))
        modules = {n.module for n in ast.walk(tree) if isinstance(n, ast.ImportFrom)}
        self.assertFalse({"jarvis", "secure_sqlite", "tailnet_access"} & modules)

if __name__ == "__main__":
    unittest.main()
