# Strategy: schema, storage decisions, and test plan

Companion to SPEC.md. SPEC.md is the what; this is the how, plus the decisions
that were open. Read this before writing code, and keep it honest as things change.

## Decisions

### Storage: do we need S3? Can transcripts live in the DB?

Short answer: no S3 for now, and yes, transcripts belong in Postgres.

- Transcripts, summaries, action items, embeddings are all text or vectors. A one
  hour meeting is roughly 8k to 12k words, about 60 to 90 KB of text. A hundred
  meetings is single digit megabytes. Neon handles this without noticing. Keeping
  it in Postgres means one query surface for display, search, and analytics, and
  zero extra infrastructure. This is the right call.
- The only large binary is the original audio. Storing audio as `bytea` in Postgres
  is an anti pattern: it bloats the database, slows backups, and burns Neon storage.
  So we do not persist raw audio. We transcribe the uploaded bytes in a temp file,
  then discard them. The meetings table keeps a nullable `audio_uri` column as a
  seam, so adding object storage (Vercel Blob, R2, or S3) later is a one field
  change with no schema churn and no rework.
- Conclusion: S3 is overkill for the assignment. Revisit only if we add audio
  playback or re transcription, and even then a blob store beats Postgres for the
  bytes.

### Model

- Dev and debugging: `gpt-5-mini`. Cheapest mini tier on the account, good enough
  for extraction while I iterate. Set in `.env` as `OPENAI_MODEL`.
- Demo and quality: `gpt-5.5` (or `gpt-5.4`). One env flip, no code change.
- `gpt-5.5-mini` and `gpt-5.5-nano` do not exist on the account. The 5.5 line is
  full and pro only.
- Reasoning models: set `reasoning.effort` low (or minimal) for extraction to keep
  latency and cost down. Extraction is structured, not a reasoning marathon.
- Embeddings: `text-embedding-3-small`, 1536 dims, matches the vector column.

### Database connection (Neon specifics)

- Driver is psycopg v3. asyncpg cannot parse Neon's `sslmode` and
  `channel_binding` libpq params, psycopg can. SQLAlchemy URL uses the
  `postgresql+psycopg://` scheme, derived from `DATABASE_URL` at config time.
- Neon's pooled endpoint is PgBouncer in transaction mode. Disable client side
  prepared statements (`prepare_threshold=None`) so pooling does not break.
- Migrations and integration tests do not run against Neon. Integration tests use
  an ephemeral local pgvector Postgres (docker) for isolation and speed. Neon is
  the dev runtime and the target for the manual and e2e runs.

## Data model

UUID primary keys (`gen_random_uuid()`), `timestamptz` defaults, FKs cascade on
delete so removing a meeting cleans up everything under it. Segments are the single
source of truth for the transcript; the full labelled text is rebuilt in memory for
extraction rather than stored twice.

- `meetings`
  - id, title, filename, audio_uri (nullable), duration_sec (nullable),
    language (nullable), status, error (nullable), created_at, updated_at
  - status enum: uploaded | transcribing | extracting | indexing | done | failed
- `speakers`
  - id, meeting_id (fk), label (int, Deepgram index), display_name (nullable)
  - unique (meeting_id, label). Renaming a speaker is a write here, no reprocessing.
- `segments`
  - id, meeting_id (fk), idx (int, order), speaker_label (int),
    start_sec (float), end_sec (float), text
  - index on meeting_id. Drives the transcript view and speaking time analytics.
- `summaries`
  - id, meeting_id (fk, unique), overview (text),
    attendees / key_decisions / discussion_points / open_questions / next_steps
    (jsonb arrays of strings)
- `action_items`
  - id, meeting_id (fk), idx, task, owner (nullable), due (nullable, free text so
    "next Friday" survives), completed (bool, default false), created_at
- `transcript_chunks`
  - id, meeting_id (fk), idx, text, start_sec, end_sec,
    embedding Vector(1536), ts tsvector (generated from text, GIN indexed)
  - HNSW index on embedding with vector_cosine_ops
- `meeting_topics`
  - id, meeting_id (fk), topic (text), idx
  - index on topic. Powers recurring topics across meetings via GROUP BY.
- Agent sessions: created and owned by the Agents SDK `SQLAlchemySession`. We do not
  hand model these; they live in their own tables in the same database.

## Module boundaries

We dropped the heavy provider abstraction. We still keep thin seams where they buy
testability, nothing speculative:

- `transcription/` one function that takes audio bytes and returns parsed segments.
  The Deepgram client is injected so tests pass a fake and never hit the network.
- `extraction/` one function: labelled transcript in, structured summary plus action
  items out, via the Responses API. OpenAI client injected.
- `indexing/` pure chunking, then embed (client injected), then persist.
- `retrieval/` pure RRF fusion over a vector query and a full text query.
- `agent/` the Agents SDK agent plus the `search_archive` tool wrapping retrieval.
- `analytics/` relational aggregation queries.
- FastAPI wires these with `Depends` for the session and the clients, which is also
  how tests override them.

## Test strategy (write tests first, per phase)

Three layers, runnable independently.

- Unit (`tests/unit/`, no network, no DB): the deterministic cores.
  - Deepgram response to segments mapping (fixture JSON in, segments out, including
    speaker change boundaries and timestamp math).
  - Chunking: token or char windows with overlap, boundary correctness, idx order.
  - RRF fusion: ranking math, ties, items present in one list but not the other.
  - Extraction response mapping to ORM rows (fixture model in, rows out).
- Integration (`tests/integration/`, local pgvector via docker, external APIs mocked):
  - Migrations apply cleanly, extension and indexes exist.
  - CRUD and the vector plus full text hybrid query return expected ordering on
    seeded data.
  - FastAPI endpoints via httpx AsyncClient with dependency overrides: upload starts
    the pipeline (mocked Deepgram and OpenAI), status transitions, speaker rename,
    action item toggle, ask returns an answer with citations, analytics aggregates.
- End to end (`tests/e2e/`, opt in marker, real APIs, costs a little):
  - A short real audio sample runs the whole pipeline against gpt-5-mini and real
    Deepgram, then a few natural language queries hit the archive. Asserted loosely
    (sections present, at least N action items, query returns the right meeting),
    since model output is not deterministic.

Test infra: pytest, pytest-asyncio, httpx. DB fixture starts an ephemeral pgvector
container, runs migrations once, and wraps each test in a transaction that rolls
back. External clients are faked via fixtures and FastAPI dependency overrides.
E2E is gated behind `-m e2e` so the default suite stays fast and free.

A phase is done only when its tests are green. Backend fully tested before frontend.

## Tooling

- Backend: `uv` for env and deps, `ruff` for lint and format, `pytest` for tests,
  `alembic` for migrations. Run via `uv run`.
- Frontend: Next.js 16 App Router, TypeScript, Tailwind. Built and exercised after
  the backend is solid.

## Phase gates (mirrors SPEC phases, with the test that closes each)

0. Scaffold: uv project, config loads env, FastAPI `/health` returns ok. Test: health
   endpoint, config parsing.
1. Transcription: Deepgram adapter and parser. Test: fixture to segments (unit).
2. Persistence: models and migration, store meeting and segments. Test: migration and
   round trip (integration).
3. Extraction: Responses API structured output to summary and action items. Test:
   mapping (unit) plus persisted via endpoint (integration, mocked).
4. Indexing: chunk, embed, store vectors and tsvector. Test: chunking (unit), rows and
   indexes present (integration).
5. Retrieval: hybrid RRF. Test: fusion math (unit), ordering on seeded data (integration).
6. Agent: agent plus search tool plus sessions plus tracing, `POST /ask`. Test: ask
   returns answer with citations (integration, mocked tool), one real (e2e).
7. Analytics: aggregation queries and endpoint. Test: aggregates on seeded data.
8. Wiring: background pipeline and status polling, CORS, upload guard. Test: full
   mocked pipeline e2e through the API.
9. Frontend: upload, transcript with editable speaker names, checklist, search, dashboard.
10. Demo pass: real sample audio end to end against the five success metrics.
