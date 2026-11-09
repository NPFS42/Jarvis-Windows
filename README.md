# Jarvis for Windows

**Public, standalone Windows frontend for a privately operated Jarvis AI coordinator.**

This repository contains a desktop client only. Jarvis's backend source, agent tools, SQLCipher database, private memory, model files, n8n setup, private server credentials, Tailscale hostnames and personal history are NOT bundled or published.

- Main (private) Jarvis project: [NPFS42/Jarvis-Local-Agent](https://github.com/NPFS42/Jarvis-Local-Agent). Access is restricted intentionally.
- Public Android frontend: [NPFS42/Jarvis-Android](https://github.com/NPFS42/Jarvis-Android).
- License: AGPL-3.0-only for project-owned code; dependencies retain their own licenses.

## Application behavior

A single portable Jarvis-Frontend.exe runs with an embedded Chromium-based Microsoft WebView2 window. It does not open a separate Chrome/Edge tab and does not need a separately installed Python runtime for the UI. It **does** require the OS-provided WebView2 Runtime. A compatible private Jarvis backend and local Ollama installation must be set up separately if hosting an AI on this PC.

1. Check localhost port 8765 for the real Jarvis interface, and attach if available.
2. If the local service is stopped, ASK before launching an already installed private Jarvis source tree. The frontend does not install/download it or invent a second database.
3. If the local service cannot start or the user declines, ASK before checking the signed-in Tailscale peer list. Only online devices linked to the same Tailscale owner account are candidates.
4. Verify peer MagicDNS names, Tailscale IP ranges, normal HTTPS certificates, and the authenticated full-access Jarvis identity marker. ASK before connecting.
5. Display only the selected local/tailnet origin in Chromium WebView2. Block other websites, LAN shortcuts, file URLs and popups.

The private server's existing authorization still applies. This frontend does not grant Windows administrator rights.

## Build

On Windows 10 or later, x64, with Python 3.13 for the build and an installed WebView2 Runtime:

    powershell -NoProfile -ExecutionPolicy Bypass -File .\build.ps1

Output: dist/Jarvis-Frontend.exe. The executable bundles the Python UI shim and pywebview, but **not private Jarvis code**. Unit tests and a packaged smoke check run during build. Public GitHub Actions builds an **unsigned** frontend artifact.

## Local/private installation

If the backend is installed in a non-standard path, set the current-user JARVIS_BACKEND_ROOT environment variable to its source directory containing jarvis.py, ui.html and the already initialized encrypted runtime. The frontend prompts before attempting to run it via that PC's existing Python runtime. If absent, use verified Tailscale remote access instead.

If the backend is on a different PC, install and sign in to Tailscale on Windows and configure Tailscale Serve on the host. The frontend itself never enables public Tailscale Funnel or opens a network listener.

## Signing and availability

This first public executable is intentionally UNSIGNED. A trusted Windows Authenticode code-signing certificate was not found on the development machine. A public build is not equivalent to an Authenticode-signed production installer; do not bypass security warnings for unverified binaries. Physical testing, a production signing certificate, verified Windows SmartScreen reputation, upgrade/install tests and a clean-account security review are remaining release gates.

## Privacy

No telemetry, ads, contact/microphone capture or analytics. All session content travels directly between this client and the selected local or owner-authorized Tailscale Jarvis node. Jarvis's server is responsible for storing and protecting its own memories. See [PRIVACY.md](PRIVACY.md).
