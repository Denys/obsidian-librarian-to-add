from __future__ import annotations

import json
import threading
import urllib.error
import urllib.request
from pathlib import Path

from obsidian_librarian.gui.server import create_server


def _request(url: str, token: str | None = None, payload: dict | None = None) -> tuple[int, dict]:
    data = None if payload is None else json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(url, data=data)
    if token is not None:
        request.add_header("X-Gui-Token", token)
    if payload is not None:
        request.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(request, timeout=5) as response:
            return response.status, json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        return exc.code, json.loads(exc.read().decode("utf-8"))


def test_gui_server_health_actions_and_token_gate(tmp_path: Path) -> None:
    httpd, token, url = create_server("127.0.0.1", 0, tmp_path)
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    try:
        status, body = _request(f"{url}/api/health", token)
        assert status == 200
        assert body["status"] == "ok"
        assert body["vault"] == str(tmp_path.resolve(strict=False))

        status, body = _request(f"{url}/api/actions", token)
        assert status == 200
        assert any(action["id"] == "librarian_ingest" for action in body["actions"])

        status, body = _request(f"{url}/api/actions")
        assert status == 401
        assert body["status"] == "error"

        status, body = _request(f"{url}/api/actions", "bad-token")
        assert status == 401
        assert body["status"] == "error"
    finally:
        httpd.shutdown()
        httpd.server_close()
        thread.join(timeout=5)


def test_gui_run_route_returns_confirmation_for_write_action(tmp_path: Path) -> None:
    inbox = tmp_path / "00_Inbox"
    inbox.mkdir()
    (inbox / "note.md").write_text("# Note\n", encoding="utf-8")

    httpd, token, url = create_server("127.0.0.1", 0, tmp_path)
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    try:
        status, body = _request(
            f"{url}/api/run",
            token,
            {
                "action_id": "librarian_ingest",
                "params": {"inbox": str(inbox), "vault": str(tmp_path), "mode": "draft"},
                "confirmed": False,
            },
        )

        assert status == 200
        assert body["status"] == "needs_confirmation"
        assert body["executed"] is False
        assert not (tmp_path / "90_Staging").exists()
    finally:
        httpd.shutdown()
        httpd.server_close()
        thread.join(timeout=5)
