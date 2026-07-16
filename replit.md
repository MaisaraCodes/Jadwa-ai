# Jadwa.ai — منصة جدوى

AI-powered credit assessment platform for Saudi SME financing. Two portals (SME owner + credit officer) backed by a multi-agent LangGraph pipeline.

## Stack

| Layer | Tech |
|-------|------|
| Frontend | React 18 + TypeScript + Vite + Tailwind CSS |
| Backend | FastAPI (Python 3.12) + LangGraph + OpenAI |
| Auth / DB | Supabase (Postgres + pgvector + Storage) |

## Running locally on Replit

Two workflows are configured:

1. **Backend API** — FastAPI on port 8000 (console output)
   ```
   cd backend && uvicorn main:app --host 0.0.0.0 --port 8000 --reload
   ```
2. **Start application** — Vite frontend on port 5000 (webview)
   ```
   cd frontend && npm install --silent && npm run dev
   ```

The Vite dev server proxies all `/api/*` requests to `localhost:8000`, so the frontend and backend appear as one origin in the browser.

## Required secrets

Set in Replit Secrets (already configured):

| Secret | Purpose |
|--------|---------|
| `OPENAI_API_KEY` | All model nodes (vision, mini, full, embeddings) |
| `SUPABASE_URL` | Supabase project URL (backend) |
| `SUPABASE_ANON_KEY` | JWT validation (backend) |
| `SUPABASE_SERVICE_ROLE_KEY` | Bypasses RLS — backend only |
| `SUPABASE_JWT_SECRET` | Validates Supabase JWTs in FastAPI |
| `VITE_SUPABASE_URL` | Supabase URL (frontend) |
| `VITE_SUPABASE_ANON_KEY` | Anon key (frontend) |

## Non-secret env vars (shared)

Set via Replit environment variables:

- `OPENAI_MODEL` / `OPENAI_MODEL_MINI` / `OPENAI_MODEL_VISION` — pinned to `gpt-4o` / `gpt-4o-mini`
- `OPENAI_EMBEDDING_MODEL` — `text-embedding-3-large`
- `ENABLE_MOCK_OPEN_BANKING=true` — use mock bank data in development
- `LANGCHAIN_TRACING_V2=false` — set to `true` + add `LANGCHAIN_API_KEY` to enable LangSmith tracing

## Project structure

```
backend/          FastAPI app
  core/           Auth, Supabase clients, LangGraph orchestration
  nodes/          LangGraph agent nodes
  routers/        API route handlers
  schemas/        Pydantic models
frontend/
  src/            React app
data/             Synthetic data + oracle corpus scripts
docs/             Architecture, API contract, design system
design-mocks/     HTML prototypes
supabase/         DB migrations
```

## User preferences

- Keep existing project structure and stack — do not restructure or migrate.
