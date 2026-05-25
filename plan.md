# PromptManager Refactor Plan

## Goal

Extract the prompt management core from the current Django/MongoDB application so the product can evolve in layers:

```text
UI
  -> frontend/backend framework
  -> prompt management core algorithms
  -> storage interfaces
  -> DB and persisted document structure
```

The end state is a core that can be tested without Django, MongoDB, browser UI, or Azure OpenAI dependencies.

## Current State

- Django app serves both API endpoints and the single-page UI.
- `prompts/services.py` currently mixes validation, MongoDB access, document serialization, prompt versioning, channel assignment, prompt rendering, and LLM test execution.
- `prompts/views.py` is mostly HTTP request/response glue, but it directly pulls concrete repositories from service factory functions.
- MongoDB document shape is embedded in repository code rather than isolated behind stable domain models and storage ports.
- Prompt rendering and validation are present, but not separated as reusable core algorithms.
- Several user-facing strings appear mojibake/corrupted and should be fixed before or during the refactor.

## Target Architecture

```text
prompts/
  web/
    views.py
    urls.py
    serializers.py
  application/
    prompt_workflow.py
    prompt_testing.py
  core/
    models.py
    validation.py
    renderer.py
    versioning.py
    channels.py
    errors.py
  ports/
    repositories.py
    llm_provider.py
  infrastructure/
    mongo/
      repositories.py
      documents.py
    llms/
      azure_openai.py
      preview.py
```

Layer rules:

- `core/` contains pure business rules and has no Django, PyMongo, HTTP, or environment variable imports.
- `application/` coordinates workflows and depends on core plus repository/provider interfaces.
- `ports/` defines storage and LLM interfaces.
- `infrastructure/` adapts MongoDB and LLM providers to those interfaces.
- `web/` adapts Django requests/responses to application services.
- Existing API behavior should be preserved during migration unless a change is explicitly planned.

## Core Domain Model Draft

- `PromptIdentity`: department/type, sub-department/category, prompt name.
- `Prompt`: identity, description, versions, channels, timestamps.
- `PromptVersion`: stable id, version number, role character, content, notes, created metadata.
- `ChannelMapping`: channel name to version id.
- `RenderedPrompt`: rendered system prompt and request preview messages.
- `PromptTestRequest`: selected version or channel, variables, user input.

## Storage Port Draft

```python
class PromptRepository(Protocol):
    def list_tree(self) -> PromptTree: ...
    def get(self, identity: PromptIdentity) -> Prompt: ...
    def save_version(self, draft: PromptVersionDraft) -> Prompt: ...
    def assign_channel(self, identity: PromptIdentity, channel: str, version: int) -> Prompt: ...
    def delete_channel(self, identity: PromptIdentity, channel: str) -> Prompt: ...
    def delete_version(self, identity: PromptIdentity, version: int) -> Prompt: ...
    def delete_prompt(self, identity: PromptIdentity) -> None: ...
```

MongoDB implementation details stay behind this interface.

## Refactor Phases

### Phase 0: Baseline and Safety

- Commit the current PromptManager version as an independent repository.
- Ensure `.env`, `.venv`, caches, and local artifacts are ignored.
- Run `python manage.py check` and record any current failures.
- Add a small smoke test or fixture around current service behavior before moving code.

### Phase 1: Extract Pure Core

- Move shared errors and validation helpers into `prompts/core/errors.py` and `prompts/core/validation.py`.
- Extract prompt rendering into `prompts/core/renderer.py`.
- Extract version/channel selection rules into `prompts/core/versioning.py` and `prompts/core/channels.py`.
- Add focused tests for validation, rendering, channel selection, and version deletion rules.

### Phase 2: Introduce Application Services

- Create `PromptWorkflowService` for create/update/delete/list/detail/channel workflows.
- Create `PromptTestingService` for inline and stored prompt testing.
- Make Django views call application services instead of concrete Mongo repositories.
- Keep response payloads compatible with the current frontend.

### Phase 3: Isolate Storage

- Define repository protocols in `prompts/ports/repositories.py`.
- Move MongoDB-specific document reads/writes into `prompts/infrastructure/mongo/repositories.py`.
- Add Mongo document mappers so DB field names such as `promptname`, `prompts`, `create_at`, and `note` do not leak into core/application code.
- Decide whether to keep the current nested MongoDB shape or migrate toward flatter collections.

### Phase 4: Isolate LLM Providers

- Move LLM provider interface into `prompts/ports/llm_provider.py`.
- Keep Azure OpenAI and preview mode under `prompts/infrastructure/llms/`.
- Make prompt testing depend on the provider interface only.

### Phase 5: Frontend/API Cleanup

- Move API-specific parsing and response shaping into serializers/adapters.
- Fix corrupted UI/API messages.
- Add API tests for core workflows.
- Review frontend data contracts after backend layering is stable.

### Phase 6: Package Boundary

- If the boundaries are clean, consider extracting `core/`, `application/`, and `ports/` into a standalone package.
- Keep Django/MongoDB as one deployable adapter around that package.

## Suggested First Implementation Order

1. Add tests around `SafeTemplateMap`, prompt rendering, version selection, and channel mapping.
2. Extract renderer and validation helpers without changing behavior.
3. Introduce core models as plain dataclasses.
4. Move Mongo serialization/deserialization into mapper functions.
5. Add repository protocols and make Mongo repository implement them.
6. Update views to use application service factories.

## Open Decisions

- Repository name on GitHub: default proposal is `PromptManager`.
- Whether the future standalone package should be Python-only or expose an HTTP-independent CLI as well.
- Whether MongoDB should keep nested prompt versions or move to flatter version documents.
- Whether prompt templates should remain Python `format_map` syntax or move to explicit `{{variable}}` syntax.
- Whether channel mappings should point to version numbers or stable version ids only.
