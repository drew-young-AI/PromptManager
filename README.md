# Healthcare Prompt Manager

Healthcare Prompt Manager is a Django 6 application for managing system prompts in MongoDB with PyMongo. It stores prompts in a four-layer hierarchy:

- Type
- Category
- Prompt name
- Prompt versions and data

The UI is a single-page, pure JavaScript interface for browsing prompts, saving new versions, mapping versions to release channels such as production, alpha, and beta, and testing prompts on the same page.

## Stack

- Python 3.12+ virtual environment
- Django 6.0.3
- MongoDB
- PyMongo
- Pure JavaScript frontend

## Setup

1. Create and activate a Python 3.12+ virtual environment.
2. Install dependencies from `requirements.txt`.
3. Copy `.env.example` to `.env` and set MongoDB values.
4. Start Django with `python manage.py runserver`.

Example setup:

```bash
python3.13 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
python manage.py runserver
```

## Codex CLI

This repository includes a Codex-compatible skill at `codex/skills/prompt-manager`.
Install it into your local Codex home with:

```powershell
.\codex\install-skills.ps1
```

The skill helps Codex work on the Django app, prompt core extraction, MongoDB storage adapters, and prompt run metadata without depending on UI or endpoint details.

## Docker

The repository includes a Docker development setup for Django and MongoDB.

1. Copy `.env.example` to `.env` and fill in your Azure OpenAI values.
2. Start the stack with Docker Compose.
3. Open `http://localhost:8000`.

```bash
cp .env.example .env
docker-compose up --build
```

Notes:

- The `web` container reads values from `.env`.
- `PROMPT_MANAGER_MONGODB_URI` is overridden in Compose to `mongodb://mongo:27017/`, so you do not need to change it for Docker.
- Source code is mounted into the container for live reload during development.

Useful commands:

```bash
docker-compose down
docker-compose exec web python manage.py check
docker-compose exec web python manage.py test
```

## MongoDB document shape

Each top-level document represents one prompt type. Categories, prompt names, and prompt versions are nested inside it.

```json
{
  "type": "clinical",
  "categories": [
    {
      "name": "triage",
      "prompts": [
        {
          "name": "adult-intake",
          "channels": {
            "production": 2,
            "beta": 3
          },
          "versions": [
            {
              "version": 1,
              "data": {
                "role_character": "You are a calm discharge coordinator.",
                "content": "You are a healthcare triage assistant...",
                "notes": "Initial release",
                "metadata": {
                  "department": "ER"
                }
              },
              "created_at": "2026-03-10T12:00:00+00:00",
              "created_by": "clinical.ops"
            }
          ]
        }
      ]
    }
  ]
}
```

## Live prompt testing

The test bench always shows a resolved request preview on the same page. If you also set the following environment variables, the backend will call Azure OpenAI chat completions and return the live model result:

- `PROMPT_MANAGER_LLM_PROVIDER=azure_openai`
- `PROMPT_MANAGER_AZURE_OPENAI_ENDPOINT`
- `PROMPT_MANAGER_AZURE_OPENAI_API_KEY`
- `PROMPT_MANAGER_AZURE_OPENAI_DEPLOYMENT`
- `PROMPT_MANAGER_AZURE_OPENAI_API_VERSION`

You can set `PROMPT_MANAGER_AZURE_OPENAI_ENDPOINT` either to the Azure resource URL such as `https://your-resource.openai.azure.com` or to a full Azure chat completions URL. The app will build the deployment path automatically when you provide only the resource URL.

Without those variables, the application stays in preview mode and still lets users validate the rendered system prompt and request payload.
