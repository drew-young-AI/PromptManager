---
name: prompt-manager
description: Work on the PromptManager Django application and its prompt management architecture. Use when Codex needs to run, debug, refactor, or extend PromptManager; extract prompt core logic; manage prompt versions, channels, prompt runs, metadata, MongoDB storage, or Azure OpenAI test execution.
---

# PromptManager

Use this skill when working inside the PromptManager repository.

## Verify Locally

From the repository root:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe manage.py check
.\.venv\Scripts\python.exe manage.py runserver 127.0.0.1:8000
```

Copy `.env.example` to `.env` for local MongoDB and Azure OpenAI settings. Never commit `.env`.

## Refactor Rules

Follow `plan.md` as the architecture source of truth.

- Keep Django views as request/response adapters.
- Move workflow coordination into application services.
- Keep prompt rendering, validation, versioning, channel selection, and run recording in core modules with no Django or PyMongo imports.
- Put MongoDB document mapping and persistence behind repository interfaces.
- Put Azure OpenAI and preview providers behind LLM provider interfaces.
- Preserve existing frontend/API payload compatibility unless a task explicitly changes it.

## Important Domain Concepts

- `Prompt`: named prompt with department/category identity.
- `PromptVersion`: immutable version content and creation metadata.
- `Channel`: release alias such as production, alpha, or beta.
- `ExternalContext`: snapshot of imported outside data such as medical records, MCP output, files, or manual input.
- `PromptRun`: auditable record of a rendered prompt, external context snapshot, variables, model/provider, output, and metadata.

Prefer storing dynamic prompt run data in MongoDB, not `.env`. Use `.env` only for runtime configuration and secrets.
