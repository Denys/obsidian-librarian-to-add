# Deployment

The first supported deployment is a local process:

```powershell
cd C:\Users\denko\Codex\obsidian-librarian-to-add\experiments\agents-sdk\olp-agent
.\.venv\Scripts\python.exe main.py serve --host 127.0.0.1 --port 8421
```

Readiness:

```powershell
Invoke-RestMethod http://127.0.0.1:8421/health
```

The HTTP app is intentionally local-only by default. Do not bind to `0.0.0.0` or expose through a tunnel without adding authentication, deciding the target vault policy, and verifying the OLP GUI/agent access path separately.

The OpenAI cookbook Deployment Manager can be tested later. This app already provides the basic manager signals: `pyproject.toml`, `openai-agents`, `PORT`-compatible service entrypoint, and `/health`.
