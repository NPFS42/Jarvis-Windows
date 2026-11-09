"""Jarvis for Windows -- PUBLIC frontend only; private coordinator is NOT bundled.

Build with pywebview + PyInstaller; requires system Microsoft Edge WebView2.
The AI model, memories, tools, HTTP service, backend source and credentials all
remain in the separately installed private Jarvis system.
"""
from __future__ import annotations

import ctypes
import ipaddress
import json
import os
import shutil
import socket
import subprocess
import sys
import time
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import HTTPRedirectHandler, ProxyHandler, Request, build_opener

APP_NAME = "Jarvis — Windows Frontend"
LOCAL = "http://127.0.0.1:8765/"
MARKER = "STARS-JARVIS-FULL-v1"
TS_V4 = ipaddress.ip_network("100.64.0.0/10")
TS_V6 = ipaddress.ip_network("fd7a:115c:a1e0::/48")
OPENER = build_opener(ProxyHandler({}))
MAX_PEERS = 20


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        return None


STRICT = build_opener(ProxyHandler({}), NoRedirect)


def is_tailscale_address(addr: str) -> bool:
    try:
        ip = ipaddress.ip_address(addr)
        return ip in TS_V4 or ip in TS_V6
    except ValueError:
        return False


def valid_tailnet_host(host: str) -> bool:
    import re
    return (isinstance(host, str) and len(host) <= 253 and bool(
        re.fullmatch(r"[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?(?:\.[a-z0-9-]+)+\.ts\.net",
                     host.lower())))


def allowed_navigation(url: str, selected: str) -> bool:
    """Reject remote navigation, userinfo, injected protocols and rogue ports."""
    try:
        actual, expected = urlsplit(url), urlsplit(selected)
        return (actual.scheme == expected.scheme and actual.hostname == expected.hostname
                and actual.username is None and actual.password is None
                and (actual.port or (443 if actual.scheme == "https" else 80))
                == (expected.port or (443 if expected.scheme == "https" else 80))
                and ((expected.scheme == "http" and expected.hostname == "127.0.0.1"
                      and expected.port == 8765)
                     or (expected.scheme == "https"
                         and valid_tailnet_host(expected.hostname or ""))))
    except ValueError:
        return False


def local_status() -> str:
    try:
        with OPENER.open(LOCAL, timeout=2) as response:
            if response.status != 200:
                return "occupied"
            body = response.read(100_000).decode("utf-8", "replace")
            return ("ready" if "Jarvis" in body and "const token=" in body
                    and "/api/" in body else "occupied")
    except HTTPError:
        return "occupied"
    except (URLError, TimeoutError, OSError):
        return "stopped"


def tailscale_bin() -> str:
    found = shutil.which("tailscale")
    standard = Path("C:/Program Files/Tailscale/tailscale.exe")
    if found:
        return found
    if standard.is_file():
        return str(standard)
    raise RuntimeError("The Tailscale desktop client is not installed.")


def owner_peers() -> list[dict[str, str]]:
    result = subprocess.run([tailscale_bin(), "status", "--json"], timeout=8,
                            capture_output=True, text=True, check=True)
    obj = json.loads(result.stdout)
    if obj.get("BackendState") != "Running":
        raise RuntimeError("Tailscale is not connected.")
    user_id = str((obj.get("Self") or {}).get("UserID", ""))
    if not user_id:
        raise RuntimeError("No signed-in Tailscale owner identity.")
    users = obj.get("User") or {}
    owner = (users.get(user_id) or {}).get("LoginName")
    if not owner:
        raise RuntimeError("Tailscale owner identity unavailable.")
    result = []
    for item in (obj.get("Peer") or {}).values():
        if (not item.get("Online") or str(item.get("UserID", "")) != user_id):
            continue
        hostname = str(item.get("DNSName") or "").rstrip(".").lower()
        if valid_tailnet_host(hostname):
            result.append({"host": hostname, "name": str(item.get("HostName") or hostname)[:70]})
    return result[:MAX_PEERS]


def probe_host(host: str) -> bool:
    if not valid_tailnet_host(host):
        return False
    try:
        addresses = {i[4][0] for i in socket.getaddrinfo(host, 443, proto=socket.IPPROTO_TCP)}
        if not addresses or any(not is_tailscale_address(addr) for addr in addresses):
            return False
        request = Request(f"https://{host}/_jarvis/discover",
                          headers={"Accept": "application/json"})
        with STRICT.open(request, timeout=3) as response:
            if response.status != 200 or not response.headers.get("Content-Type", "").startswith("application/json"):
                return False
            obj = json.loads(response.read(2049))
        return (obj.get("service") == MARKER and obj.get("host") == host
                and obj.get("full_access") is True)
    except (OSError, ValueError, HTTPError, URLError, TimeoutError):
        return False


def message_box(text: str, *, question: bool = False) -> bool:
    if sys.platform != "win32":
        raise RuntimeError("Windows required.")
    flags = 0x24 if question else 0x10
    return ctypes.windll.user32.MessageBoxW(None, text[:1000], APP_NAME, flags) == 6


def installed_backend() -> Path | None:
    """Only a separately installed private Jarvis source tree can be started."""
    bases = [
        Path(os.environ.get("JARVIS_BACKEND_ROOT", "")) if os.environ.get("JARVIS_BACKEND_ROOT") else None,
        Path.home() / "Documents" / "STARS" / "Jarvis-Local-Agent",
    ]
    for candidate in bases:
        if candidate is None:
            continue
        candidate = candidate.expanduser().resolve()
        if (candidate / "jarvis.py").is_file() and (candidate / "ui.html").is_file() and (
            candidate / "runtime" / "private" / "sqlcipher-enabled.json"
        ).is_file():
            return candidate
    return None


def launch_existing_local() -> bool:
    """Run a private coordinator ONLY following an explicit approval dialog."""
    root = installed_backend()
    if root is None:
        message_box("A private Jarvis backend is not installed on this PC. "
                    "The frontend will search for owner-authorized tailnet instances.")
        return False
    python = shutil.which("pythonw") or shutil.which("python")
    if not python:
        py_path = Path.home() / "AppData/Local/Programs/Python/Python313/pythonw.exe"
        if py_path.is_file():
            python = str(py_path)
    if not python:
        message_box("A Python runtime for the private Jarvis backend was not found. "
                    "The Windows frontend itself needs no separate Python install.")
        return False
    try:
        subprocess.Popen([python, str(root / "jarvis.py")], cwd=str(root),
                         stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                         stderr=subprocess.DEVNULL, close_fds=True,
                         creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
    except OSError:
        message_box("The installed Jarvis service could not start.")
        return False
    for _ in range(25):
        if local_status() == "ready":
            return True
        time.sleep(0.2)
    message_box("Jarvis did not become ready on localhost.")
    return False


def choose_backend() -> str:
    status = local_status()
    if status == "ready":
        return LOCAL
    if status == "occupied":
        message_box("Port 8765 is occupied by a service that was not verified as Jarvis.")
    elif message_box("No Jarvis service is running at localhost:8765.\n"
                     "Start your separately installed local Jarvis backend?", question=True):
        if launch_existing_local():
            return LOCAL
    if not message_box("Search your signed-in Tailscale network for Jarvis instead?", question=True):
        raise RuntimeError("No Jarvis service selected.")
    try:
        peers = owner_peers()
    except (ValueError, OSError, RuntimeError, subprocess.SubprocessError) as exc:
        raise RuntimeError("Tailscale discovery unavailable. Connect and sign in to Tailscale.") from exc
    for item in peers:
        host = item["host"]
        if probe_host(host) and message_box(
            f"Connect to verified Jarvis at {item['name']}?\nhttps://{host}", question=True
        ):
            return f"https://{host}/"
    raise RuntimeError("No owner-authorized Jarvis node was selected.")


def main() -> int:
    if "--self-test" in sys.argv:
        import webview
        assert callable(webview.create_window)
        print(json.dumps({"frontend_only": True, "private_backend_bundled": False,
                          "requires_webview2": True, "local_url": LOCAL}))
        return 0
    if sys.platform != "win32":
        print("Jarvis for Windows runs on Windows.", file=sys.stderr)
        return 1
    try:
        destination = choose_backend()
        import webview
        window = webview.create_window(APP_NAME, destination, width=1320, height=900,
                                       min_size=(850, 560), background_color="#0b141b")
        if window is None:
            raise RuntimeError("Unable to create the Jarvis window.")
        webview.settings["OPEN_EXTERNAL_LINKS_IN_BROWSER"] = False

        def install_guard():
            control = window.native.browser.webview
            def navigation(sender, args):
                if not allowed_navigation(args.Uri, destination):
                    args.Cancel = True
            def popups(sender, args):
                args.Handled = True
            control.NavigationStarting += navigation
            control.CoreWebView2.NewWindowRequested += popups
            window._jarvis_guards = (navigation, popups)

        webview.start(install_guard, gui="edgechromium", debug=False,
                      private_mode=True, http_server=False)
        return 0
    except Exception as exc:
        message_box(str(exc)[:650])
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
