# Project Structure & Workflow Guidelines

> **This repository houses *internal* business‑building tools in proof‑of‑concept form.**  
> The aim is to deliver **solid and reliable code for the team’s own workflows**, not a public, at‑scale product. Iterate fast and keep intent clear, but leave the codebase tidy enough for easy hardening later.

---

## 1. Core Principles

- **Internal‑tool Prototype Mindset** – move fast to unblock business workflows. It’s okay to cut corners **as long as** they’re logged in `TODO.md`. Focus on clarity and reliability rather than internet‑scale concerns.
- **No new top‑level folders** – stay inside the tree you see today.
- **One purpose ≈ one folder** – put code where readers expect it.
- **Zero cross‑folder overlap** – interact through public interfaces only; no sneaky imports.
- **Public surfaces live in `__init__.py` barrels or FastAPI routers** – everything else stays private (prefix `_`).
- **Mirror tests to code** – same relative path under `tests/`.
- **Integrated tests early, light** – hit real services to prove the path works; cover happy flow + one failure.

---

## 2. Folder Map (What Goes Where?)

| Folder | Why it exists | Typical files |
|--------|---------------|---------------|
| `core/api_<ver>/` | HTTP contract layer (FastAPI routers) | `*_router.py`, `*_schemas.py` |
| `core/graph_<ver>/` | Microsoft Graph SDK wrappers | `*_client.py`, `*_models.py` |
| `core/openai_<ver>/` | Prompt & agent helpers | `*_agent.py`, `*_prompt.py` |
| `core/processing_<ver>/` | Business pipelines/orchestrators | `*_pipeline.py`, `processors/*.py` |
| `core/storage_<ver>/` | DB & vector‑store adapters | `*_repository.py`, `migrations/*.py` |
| `core/utils/` | Side‑effect‑free helpers | `*_util.py` |
| `docs/` | Markdown & diagrams | `index.md`, images |
| `tests/core/...` | Unit tests mirroring code | `test_*.py` |
| `tests/integration/` | Live‑service specs | `itest_*.py` |
| `tests/utils/` | Shared test helpers | `*_helper.py` |

> **Import graph**  
> `api_* → processing_* → (graph_*, openai_*, storage_*)`  
> `utils → any core folder`

CI rejects disallowed imports (`scripts/check_structure.py`).

---

## 3. Adding Code Fast

1. **Find the right folder.** If unsure, ask or log a TODO.
2. **Breaking change?** Ping maintainer to create a new `*_<major>_0_0` folder. Otherwise stay put and bump PATCH in `__version__`.
3. **Write small, typed functions (< 40 LOC).**
4. **Add one mirrored unit test.**
5. **If feature spans services, add one integration test.**
6. **Run:** `make lint test` – commit – open PR.
7. **Note shortcuts** in `TODO.md` for later refactor.

---

## 4. Testing Cheats

- **Unit tests** – quick and pure; no network/DB. Validate a single function or class in isolation.
- **Integration tests** – spin up services with Docker Compose (Postgres, vector store, live Graph) and verify service‑to‑service wiring.
- **End‑to‑End (E2E) journeys** – drive the public HTTP API with realistic payloads to confirm that _business rules & data flow_ work together (Graph ↔ Processing ↔ OpenAI ↔ Storage). Provide **one happy‑path E2E test per feature**, tagged `@pytest.mark.e2e`.
- **Coverage gate** – CI fails if total coverage < 90 % **or** any new file lacks tests (unit _or_ E2E).
- **Mark slow specs** – use `@pytest.mark.slow`; fast mode skips them (`pytest -m "not slow"`). Full E2E suite runs nightly.

---

## 5. Tooling Guard‑Rails

| Purpose | Command |
|---------|---------|
| Format & lint | `make lint` *(black, isort, flake8, pylint)* |
| Structure check | `python scripts/check_structure.py` |
| Run fast tests | `pytest -m "not slow"` |
| Full CI mirror | `make ci` |
| Local dev server | `uvicorn core.api_1_4_0.main:app --reload` |


---

## 6. When in Doubt

> **Ship the simplest thing that works, document the shortcut, and keep moving.**  
> Future‑you (or the refactor team) will thank you for the clarity.

