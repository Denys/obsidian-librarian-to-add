# Architecture

```mermaid
flowchart TD
    user["User or HTTP client"] --> main["main.py CLI / FastAPI"]
    main --> agent["OpenAI Agents SDK Agent"]
    agent --> tools["Function tools"]
    tools --> deploy["Folder deployment"]
    tools --> librarian["obsidian-librarian CLI"]
    tools --> patron["obsidian-patron CLI"]
    deploy --> target["Target library folder"]
    librarian --> target
    patron --> target
    target --> state[".olp_agent state"]
```

The app has two paths:

- Deterministic local path: `health`, `deploy-library`, `scan-library`, `classify-library`, and `plan-wave` run without an OpenAI API key.
- Live agent path: `run` and `POST /run` use `Agent`, `Runner.run`, local function tools, and typed `AgentResult`.

The tool implementation is kept outside the SDK decorator layer so tests and evals can call the same functions directly.
