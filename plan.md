# PromptManager Refactor Plan (v2.0 - Clinical AI Configuration Engine)

## Goal

Transform PromptManager from a simple CRUD tool into a **Clinical AI Configuration Engine**. 
The product will evolve in layers to support distinct user roles and high-rigor medical environments:

```text
UI (Healthcare Interface)
  -> Frontend/Backend framework
  -> Prompt Optimization Engine (Meta-prompting)
  -> Contextual Resolver (Dept/Scenario aware)
  -> Prompt management core algorithms
  -> Storage interfaces (Prompt Hierarchy + Medical Records)
```

## Core Vision: Power User vs. General User

### 1. Power User (Clinical Designer)
- **Role**: Defines prompt logic based on **Department** (e.g., ER, Cardiology) and **Clinical Scenario** (e.g., Triage, Post-op).
- **Optimization Button**: Implementation of a **Meta-prompting** feature that refines raw clinical instructions into structured, high-performance prompts, providing "peace of mind" and engineering consistency.
- **Workflow**: Design -> Optimize -> Versioning -> Channel Assignment (Alpha/Beta/Prod).

### 2. General User (Clinical Consumer)
- **Role**: Consumes the "Production" version of a prompt without needing to see the underlying logic.
- **Context Awareness**: The system automatically resolves the correct prompt based on the user's current Department and the Patient's condition.
- **Data Integration**: Optimized prompts are combined with patient records (from MongoDB) to generate clinical insights.

## Target Architecture

```text
prompts/
  web/              # Django API (Stable Data Contract for UI)
  application/
    prompt_workflow.py
    prompt_optimization.py  # Meta-prompting logic
    context_resolver.py     # Dept/Scenario matching
  core/
    models.py       # ClinicalPromptIdentity (Dept, Scenario, Name)
    renderer.py     # Context-aware variable injection
    validation.py
    versioning.py
  infrastructure/
    mongo/          # Prompt storage + Medical Record access
    llms/           # Azure OpenAI + Optimization models
```

## Core Dimension Mapping
- **Dimension 1 (Department)**: Determines tone, authority, and clinical boundaries.
- **Dimension 2 (Clinical Scenario/Disease)**: Determines medical knowledge scope and data requirements.

## Refactor Phases

### Phase 0: Baseline and Safety
- [DONE] Commit current state as a save point.
- [DONE] Establish remote MongoDB connectivity (192.168.137.232).
- [DONE] Seed initial clinical test data.

### Phase 1: Extract Pure Core & Define Clinical Context
- Extract `renderer.py` and `validation.py`.
- Define `ClinicalPromptIdentity` in `core/models.py` to support Department/Scenario dimensions.
- Ensure renderer supports dynamic context injection.

### Phase 2: Optimization Engine (The "Meta-Prompt" Button)
- Implement `application/prompt_optimization.py`.
- Define the "Master Meta-Prompt" for healthcare consistency.
- Integrate with Azure OpenAI to provide the "Optimize" service.

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
