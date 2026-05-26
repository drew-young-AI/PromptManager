# Codex Notes

This repository is a Django-based prompt management app.

## Local Verification

Use an isolated virtual environment:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe manage.py check
```

The app reads local runtime settings from `.env`. Do not commit `.env`, secrets, database dumps, or virtual environments.

## Architecture Direction

Keep the refactor aligned with `plan.md`:

- UI and Django views are adapters.
- Application services coordinate workflows.
- Prompt core logic stays free of Django, PyMongo, HTTP, and provider-specific imports.
- MongoDB and LLM providers are infrastructure adapters behind interfaces.

Preserve the existing HTTP response shape while extracting core behavior unless a change is explicitly requested.
