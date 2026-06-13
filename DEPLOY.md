# Deploying

Backend (FastAPI) and frontend (Next.js) deploy as two services from this one repo.
The database stays on Neon. Recommended host: Railway, because the backend runs the
ingestion pipeline as a background task after responding, which needs a persistent
container (a request-scoped serverless function would be frozen mid-transcription).

## 1. Backend service (Railway)

- New service from this GitHub repo. Set **Root Directory** to `backend`.
- Railway detects `backend/Dockerfile` and builds it. The container runs
  `alembic upgrade head` then starts uvicorn on `$PORT`.
- Variables:
  - `DATABASE_URL` — the Neon pooled URL (same one used locally)
  - `DEEPGRAM_API_KEY`, `OPENAI_API_KEY`
  - `OPENAI_MODEL` — `gpt-5.5` for the demo, or `gpt-5-mini` to keep costs low
  - `OPENAI_EMBEDDING_MODEL` — `text-embedding-3-small`
  - `MAX_UPLOAD_MB` — e.g. `200`
  - `FRONTEND_ORIGIN` — the frontend's public URL (set after step 2), for CORS
- Generate a public domain for the service and note the URL.

## 2. Frontend service (Railway)

- New service from the same repo. Set **Root Directory** to `frontend`
  (Nixpacks: `npm run build` then `npm run start`).
- Variables:
  - `NEXT_PUBLIC_API_BASE_URL` — the backend's public URL from step 1.
    This is inlined at build time, so it must be set before the build runs.
- Generate a public domain.

## 3. Close the loop

1. Deploy the backend, copy its URL.
2. Set the frontend's `NEXT_PUBLIC_API_BASE_URL` to that URL, deploy the frontend.
3. Set the backend's `FRONTEND_ORIGIN` to the frontend URL and redeploy the backend
   so CORS allows it.

## Notes

- Migrations run on every deploy (idempotent). The Neon schema is already current.
- On restart, any meeting left mid-processing is marked `failed` automatically, so
  nothing stays stuck.
- The frontend can alternatively run on Vercel; only the env var wiring changes.
