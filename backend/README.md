# jobact-backend

The JobAct backend: a contract-first modular monolith (FastAPI + SQLAlchemy async +
PydanticAI/LiteLLM) implementing Milestone 1 — Google sign-in, customers, visits,
AI-drafted reports, real signature capture, and signed PDF generation. See
[`CLAUDE.md`](CLAUDE.md) for layering rules and the full command reference, and
[`../docs/architecture/overview.md`](../docs/architecture/overview.md) for the design.

## Setup

```bash
cp .env.example .env   # fill in OPENROUTER_API_KEY for real AI drafting; other defaults work
docker compose up -d   # Postgres 17, Redis 8, MinIO (+ bucket init), LiteLLM
uv sync --dev
uv run alembic upgrade head
```

## Run

```bash
uv run uvicorn jobact.apps.api.main:app --reload --port 8000   # API
uv run python -m jobact.apps.worker                            # worker (separate process)
```

## Test

```bash
uv run pytest                 # domain/contract/workflow tests run without Docker;
                               # tests/integration/ needs `docker compose up -d` first
```

See [`CLAUDE.md`](CLAUDE.md) for what each test directory covers, and
[`../docs/architecture/ai.md`](../docs/architecture/ai.md) for the (currently missing)
opt-in live-model smoke test this project still owes itself.
