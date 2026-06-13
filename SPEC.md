# Meeting Intelligence Platform: Spec & Build Plan

Turn a meeting recording into a speaker-labelled transcript, a structured summary,
an action-item checklist, and a searchable archive you can ask questions of.
Upload-only for now (live capture is out of scope, see end).

## Stack (pinned)

Backend: Python 3.11+, FastAPI.

| Concern          | Choice                          | Version  |
|------------------|---------------------------------|----------|
| STT + diarization| deepgram-sdk (model `nova-3`)   | 7.3.1    |
| LLM extraction   | openai (Responses API)          | 2.41.1   |
| Agent / Q&A      | openai-agents                   | 0.17.5   |
| Web framework    | fastapi + uvicorn[standard]     | 0.136.3 / 0.49.0 |
| ORM              | sqlalchemy (async) + psycopg v3 | 2.0.50 / 3.3.4 |
| Vectors          | pgvector (python) + Postgres    | 0.4.2 / pg18 |
| Migrations       | alembic                         | 1.18.4   |
| Frontend         | Next.js (App Router, TS, Tailwind) | 16    |

Single Postgres holds everything: relational rows for analytics, `vector` column
for semantic search, generated `tsvector` for keyword search, and the agent's
session history (`SQLAlchemySession`). No second datastore.

Local DB:
```
docker run -d --name mtg-pg -p 5432:5432 \
  -e POSTGRES_USER=meeting -e POSTGRES_PASSWORD=meeting -e POSTGRES_DB=meeting_intel \
  -v mtg_pgdata:/var/lib/postgresql/data pgvector/pgvector:pg18-trixie
```

## Architecture

```
Next.js (upload, transcript, checklist, search, dashboard)
        │ HTTP (multipart upload direct to backend; JSON for the rest)
        ▼
FastAPI
  ingestion pipeline (background task, status-polled):
    transcribe ──> persist ──> extract ──> index
     Deepgram      Postgres     OpenAI      embed + tsvector
  query:
    Agents SDK agent ─ tool: search_archive ─> hybrid retrieval (RRF)
                     ─ session history in Postgres, tracing on
  analytics: relational GROUP BY queries
```

The pipeline is plain linear code, one function per stage, no framework.
The agent is the only place orchestration earns its keep.

## Data model

- `meetings`: id, title, filename, duration_sec, status, created_at.
  status flows: `uploaded -> transcribing -> extracting -> indexing -> done` (or `failed`, with error).
- `speakers`: id, meeting_id, label (int from Deepgram), display_name (nullable, user-assigned).
- `segments`: id, meeting_id, speaker_label, start, end, text.
  Source of the transcript view and of speaking-time analytics.
- `summaries`: id, meeting_id, attendees[], key_decisions[], discussion_points[],
  open_questions[], next_steps[]. JSON columns, one row per meeting.
- `action_items`: id, meeting_id, task, owner (nullable), due (nullable), completed (bool).
- `transcript_chunks`: id, meeting_id, text, embedding `Vector(1536)`,
  ts `tsvector` (generated, GIN-indexed). HNSW index `vector_cosine_ops` on embedding.

## API surface

- `POST   /meetings`            multipart audio upload, returns {id, status}; starts pipeline
- `GET    /meetings`            list with status + summary preview
- `GET    /meetings/{id}`       full detail: segments, summary, action items, speaker map
- `PATCH  /meetings/{id}/speakers`  body: {label -> display_name}; relabels transcript
- `PATCH  /action-items/{id}`   toggle completed (and edit task/owner/due)
- `POST   /ask`                 body: {question, session_id?}; runs agent, returns answer + cited meetings
- `GET    /analytics`           speaking time per speaker, meeting frequency, completion rate, recurring topics

CORS open to the frontend origin. Upload goes browser -> FastAPI directly (no Next proxy),
so we never hit Next body limits.

## Key technical notes (from current docs, do not regress)

- Deepgram: `client.listen.v1.media.transcribe_file(request=audio_bytes, model="nova-3", diarize=True, smart_format=True, utterances=True, keyterm=[...])`. Use top-level `response.results.utterances` (each carries `speaker`, `transcript`, `start`, `end`) to build `segments` directly. `keyterm` (Nova-3 only) carries technical vocab; never use legacy `keywords`.
- OpenAI extraction: `client.responses.parse(model=..., input=[...], text_format=MeetingExtract)`, read `resp.output_parsed`. Pydantic models define the summary + action-item schema.
- Embeddings: `text-embedding-3-small`, 1536 dims, matches the `Vector(1536)` column.
- Agents SDK: `@function_tool` on `search_archive(query: str) -> str` (type hints + docstring become the schema). `Runner.run(agent, question, session=SQLAlchemySession.from_url(...))`. Tracing on by default, viewable at platform.openai.com/traces.
- pgvector async: register the vector type per-connection via the `event.listens_for(engine.sync_engine, "connect")` + `run_async(register_vector_async)` hook, else `Vector` round-trips break.
- Hybrid retrieval: RRF (k=60) fusing a vector CTE (`embedding <=> qvec`) and a FTS CTE (`websearch_to_tsquery` over the generated `ts` column). No score normalization needed.
- Alembic: first migration runs `CREATE EXTENSION IF NOT EXISTS vector`; register `dialect.ischema_names["vector"] = Vector` in `env.py` to avoid autogenerate noise.

## Build phases (each one independently testable)

0. Scaffold: repo layout, deps pinned, docker Postgres up, alembic init, FastAPI healthcheck.
1. Transcription: Deepgram adapter, file bytes -> list of speaker segments. Test on a real multi-speaker sample.
2. Persistence: DB models + initial migration; store meeting + segments; `GET /meetings/{id}` returns the transcript.
3. Extraction: Responses API structured output -> summary + action items; persisted and returned.
4. Indexing: chunk transcript, embed, store vectors + tsvector with HNSW + GIN indexes.
5. Retrieval: hybrid RRF search function; eyeball top-k on a few queries.
6. Agent: Agents SDK agent + `search_archive` tool + Postgres sessions + tracing; `POST /ask` answers with citations.
7. Analytics: aggregation queries + `GET /analytics`.
8. Wiring: background pipeline + status polling, speaker relabel, action-item toggle, CORS, upload guard rail.
9. Frontend: upload, transcript viewer (editable speaker names), checklist, search/ask, analytics dashboard.
10. Demo pass: run end to end against the success metrics below; fix gaps.

## Success metrics (the bar we test against)

- Transcription WER < 10% on clear demo audio.
- Diarization separates >= 3 speakers on a test recording.
- Action-item extraction captures every explicitly stated task in the demo.
- Semantic search returns relevant results for >= 5 test queries.
- Summary has all five sections and is faithful to the recording.

## Out of scope (for now)

- Live / join-meeting capture (Deepgram streaming). Layer on after core is solid; it is the bonus.
- Multi-provider LLM abstraction. Single provider (OpenAI) until a reason to generalize appears.
```
