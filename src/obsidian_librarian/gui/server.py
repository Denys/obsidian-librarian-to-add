"""Local stdlib HTTP server for the Obsidian Librarian GUI."""

from __future__ import annotations

import argparse
import json
import secrets
import webbrowser
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from obsidian_librarian.gui.service import (
    action_registry,
    browse_directory,
    run_action,
    save_pasted_source,
)

STATIC_DIR = Path(__file__).parent / "static"
INDEX_FILE = STATIC_DIR / "index.html"


class GuiHTTPServer(ThreadingHTTPServer):
    """HTTP server carrying GUI runtime state."""

    token: str
    vault: Path


class GuiRequestHandler(BaseHTTPRequestHandler):
    """Request handler for the local GUI API."""

    server: GuiHTTPServer

    def log_message(self, _format: str, *_args: object) -> None:
        """Keep test and CLI output quiet unless routes return structured data."""

    def do_GET(self) -> None:
        path = urlparse(self.path).path
        if path == "/":
            self._send_html(self._render_index())
            return
        if path == "/api/health":
            if not self._authorized():
                self._send_json(
                    {"status": "error", "message": "Unauthorized"},
                    HTTPStatus.UNAUTHORIZED,
                )
                return
            self._send_json(
                {
                    "status": "ok",
                    "vault": str(self.server.vault.resolve(strict=False)),
                    "host": self.server.server_address[0],
                    "port": self.server.server_address[1],
                }
            )
            return
        if path == "/api/actions":
            if not self._authorized():
                self._send_json(
                    {"status": "error", "message": "Unauthorized"},
                    HTTPStatus.UNAUTHORIZED,
                )
                return
            self._send_json({"status": "ok", "actions": action_registry()})
            return
        self._send_json({"status": "error", "message": "Not found"}, HTTPStatus.NOT_FOUND)

    def do_POST(self) -> None:
        path = urlparse(self.path).path
        if not path.startswith("/api/"):
            self._send_json({"status": "error", "message": "Not found"}, HTTPStatus.NOT_FOUND)
            return
        if not self._authorized():
            self._send_json({"status": "error", "message": "Unauthorized"}, HTTPStatus.UNAUTHORIZED)
            return

        try:
            payload = self._read_json()
            if path == "/api/browse":
                self._send_json({"status": "ok", **browse_directory(payload.get("path"))})
                return
            if path == "/api/paste":
                result = save_pasted_source(
                    str(payload.get("text") or ""),
                    str(payload.get("kind") or "md"),
                )
                self._send_json({"status": "ok", **result})
                return
            if path == "/api/run":
                result = run_action(
                    str(payload.get("action_id") or ""),
                    payload.get("params") if isinstance(payload.get("params"), dict) else {},
                    confirmed=bool(payload.get("confirmed")),
                )
                self._send_json(result)
                return
        except (FileNotFoundError, PermissionError, ValueError, json.JSONDecodeError) as exc:
            self._send_json({"status": "error", "message": str(exc)}, HTTPStatus.BAD_REQUEST)
            return

        self._send_json({"status": "error", "message": "Not found"}, HTTPStatus.NOT_FOUND)

    def _authorized(self) -> bool:
        return self.headers.get("X-Gui-Token") == self.server.token

    def _read_json(self) -> dict[str, Any]:
        length = int(self.headers.get("Content-Length") or "0")
        if length == 0:
            return {}
        raw = self.rfile.read(length)
        payload = json.loads(raw.decode("utf-8"))
        if not isinstance(payload, dict):
            raise ValueError("JSON payload must be an object")
        return payload

    def _render_index(self) -> str:
        html = INDEX_FILE.read_text(encoding="utf-8")
        bootstrap = {
            "token": self.server.token,
            "defaultVault": str(self.server.vault.resolve(strict=False)),
            "serverUrl": f"http://{self.server.server_address[0]}:{self.server.server_address[1]}",
        }
        return html.replace("__GUI_BOOTSTRAP__", json.dumps(bootstrap))

    def _send_html(self, html: str, status: HTTPStatus = HTTPStatus.OK) -> None:
        data = html.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def _send_json(self, payload: dict[str, Any], status: HTTPStatus = HTTPStatus.OK) -> None:
        data = json.dumps(payload, indent=2, sort_keys=True).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)


def create_server(
    host: str = "127.0.0.1",
    port: int = 0,
    vault: str | Path = ".",
    token: str | None = None,
) -> tuple[GuiHTTPServer, str, str]:
    """Create but do not start a tokenized GUI server."""
    httpd = GuiHTTPServer((host, port), GuiRequestHandler)
    httpd.token = token or secrets.token_urlsafe(24)
    httpd.vault = Path(vault).expanduser().resolve(strict=False)
    bound_host, bound_port = httpd.server_address
    url = f"http://{bound_host}:{bound_port}"
    return httpd, httpd.token, url


def run_gui(
    *,
    vault: str | Path = ".",
    host: str = "127.0.0.1",
    port: int = 0,
    no_browser: bool = False,
) -> int:
    """Start the GUI server and block until interrupted."""
    httpd, token, url = create_server(host, port, vault)
    print(f"Obsidian Librarian GUI: {url}")
    print(f"Token: {token}")
    try:
        if not no_browser:
            webbrowser.open(url)
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping Obsidian Librarian GUI.")
    finally:
        httpd.server_close()
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="obsidian-librarian-gui",
        description="Local browser GUI for Obsidian Librarian.",
    )
    parser.add_argument("--vault", default=".", help="Default vault root path.")
    parser.add_argument("--host", default="127.0.0.1", help="Bind host.")
    parser.add_argument(
        "--port",
        type=int,
        default=0,
        help="Bind port. Use 0 for a random port.",
    )
    parser.add_argument(
        "--no-browser",
        action="store_true",
        help="Print URL without opening a browser.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    return run_gui(vault=args.vault, host=args.host, port=args.port, no_browser=args.no_browser)


if __name__ == "__main__":
    raise SystemExit(main())
