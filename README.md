# Meeting Intelligence Platform

Turn a meeting recording into a speaker-labelled transcript, a structured summary, a
checkable action-item list, and a searchable archive you can ask questions of with a great accuracy and intelligence.

## What it does

- **Transcription + diarization** with Deepgram `nova-3` (batch diarization v2). Word
  level timestamps, multiple speakers, technical-vocabulary prompting.
- **Speaker labelling** you can rename after the fact (Speaker 0 -> "Alice").
- **Structured summary**: overview, attendees, key decisions, discussion points, open
  questions, next steps. Extracted with the OpenAI Responses API into a typed schema.
- **Action items** with task, owner, and deadline, presented as a checklist.
- **Searchable archive**: hybrid retrieval (pgvector cosine similarity fused with
  Postgres full-text search via Reciprocal Rank Fusion) behind an OpenAI Agents SDK
  agent that answers natural-language questions and cites the meetings it used.
- **Analytics**: speaking time per participant, meeting frequency, action-item
  completion rate, and recurring topics across the archive.
- **Live recording**: capture straight from the microphone in the browser and feed
  the same pipeline (record, then send).
- **Manage the archive**: rename meetings, add/edit/delete action items, archive and
  restore meetings (soft delete), set a title and key terms at upload time.

The interface is an editorial "Record" design system: warm paper, a humanist serif
for headings, a grotesque for body, and mono for transcript metadata.

See `SPEC.md` for the spec and `STRATEGY.md` for schema, storage, and test decisions.

## Stack

| Layer | Choice |
|-------|--------|
| Backend | Python 3.11+, FastAPI, async SQLAlchemy, Alembic |
| Speech | Deepgram `nova-3` |
| LLM | OpenAI Responses API + Agents SDK (model via `OPENAI_MODEL`) |
| Storage | One Postgres (Neon): relational rows, pgvector embeddings, generated tsvector |
| Frontend | Next.js 16 (App Router), TypeScript, Tailwind v4 |
| Tooling | uv, ruff, pytest, testcontainers |

Ingestion is a plain linear pipeline (`transcribe -> persist -> extract -> index`) run
as a background task with status polling. The agent is the only place orchestration
earns its keep.

## Prerequisites

- Python 3.11+ and [uv](https://docs.astral.sh/uv/)
- Node.js 20+
- A Postgres database with the `pgvector` extension (Neon works out of the box)
- API keys: Deepgram and OpenAI
- Docker (only for running the integration tests)

## Setup

```bash
cp .env.example .env     # then fill in DEEPGRAM_API_KEY, OPENAI_API_KEY, DATABASE_URL
```

`OPENAI_MODEL` defaults to `gpt-5-mini` (cheap, for development). Bump it to `gpt-5.5`
for the best quality. Embeddings use `text-embedding-3-small` (1536 dims).

### Backend

```bash
cd backend
uv sync                       # create the venv and install deps
uv run alembic upgrade head   # create the schema (extension, tables, HNSW + GIN indexes)
uv run uvicorn app.main:app --reload --port 8000
```

### Frontend

```bash
cd frontend
npm install
npm run dev                   # http://localhost:3000
```

The frontend talks to the backend at `NEXT_PUBLIC_API_BASE_URL` (default
`http://localhost:8000`). Upload a recording on the home page and watch it process.

## Testing

```bash
cd backend
uv run pytest                 # unit + integration (integration spins up a pgvector container)
uv run pytest -m e2e          # opt-in: real Deepgram + OpenAI calls (costs a little)
uv run ruff check . && uv run ruff format --check .
```

Unit tests are pure and free. Integration tests run against an ephemeral pgvector
container (Docker) with each test in a rolled-back transaction, so they never touch
your real database. E2E tests hit the real APIs and are deselected by default.

A reproducible 3-speaker demo recording can be generated with:

```bash
uv --directory backend run python scripts/make_demo_audio.py demo_meeting.wav
```

## Layout

```
backend/
  app/
    transcription/  Deepgram adapter + response parser
    extraction/     Responses API structured extraction
    indexing/       chunking, embeddings, persistence
    retrieval/      hybrid search (RRF)
    agent/          Agents SDK agent + search_archive tool
    analytics/      aggregation queries
    pipeline/       the ingestion pipeline
    api/            FastAPI routers, schemas, dependencies
    models.py       SQLAlchemy ORM
  alembic/          migrations
  tests/            unit, integration, e2e
frontend/
  app/              pages: meetings, meeting detail, record, search, analytics
  components/ui/    design system: primitives, toasts, dialog
  lib/              api client, types, formatting
```
