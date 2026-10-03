# Production Deployment Guide — Nexus Pre-Sales Bot

## 1. Overview
The Nexus Pre-Sales Bot can be deployed to Vercel Serverless, Docker, or any standalone Linux VM. In production, persistent storage and production security guards are enforced.

---

## 2. PostgreSQL & pgvector Setup

### Hosted PostgreSQL Database
A production deployment requires a hosted PostgreSQL instance (e.g. Neon, Supabase, AWS RDS, or Vercel Postgres).
- Connection string format:
  ```env
  DATABASE_URL=postgresql+pg8000://user:password@host:5432/dbname?sslmode=require
  ```
  *(Note: The app automatically normalizes `postgres://` or `postgresql://` to `postgresql+pg8000://` and cleans incompatible query parameters).*

### pgvector Extension (Optional Accelerator)
- If your PostgreSQL provider supports the `vector` extension, enable it:
  ```sql
  CREATE EXTENSION IF NOT EXISTS vector;
  ```
- **Fallback behavior**: If pgvector is not installed on Postgres (or when using SQLite), `backend/app/rag/store.py:325` gracefully falls back to local Python cosine similarity over `embedding_json`. The application functions completely with or without pgvector.

---

## 3. Ingestion Architecture (Off Visitor Request Path)

In production, corpus ingestion is decoupled from visitor request handling to guarantee fast visitor response times:
1. **Deploy-Time Ingestion**:
   Run the CLI ingest script once during build or post-deploy:
   ```bash
   python -m backend.app.rag.ingest
   ```
2. **Admin API Reindexing**:
   Trigger corpus re-indexing authenticated as admin:
   ```bash
   curl -X POST https://YOUR_APP.vercel.app/admin/reindex -u admin:YOUR_UNIQUE_PASSWORD
   ```
3. **Empty Corpus Fallback**:
   If the database has not yet been indexed when a visitor arrives, the bot answers via the transparent "no verified knowledge" fallback path without blocking the visitor or timing out.

---

## 4. Mandatory Production Environment Variables

When `ENVIRONMENT=production` (or running on Vercel where `VERCEL=1`), the following environment variables **MUST** be set in your Vercel or deployment settings:

| Variable | Required Value / Format | Description & Enforcement |
|:---|:---|:---|
| `ENVIRONMENT` | `production` | Enables production security guards (admin fail-closed, SQLite refusal, CORS origin check). |
| `DATABASE_URL` | `postgresql+pg8000://...` | Hosted Postgres database. **SQLite raises `ValueError`** unless `ALLOW_EPHEMERAL_DB=true`. |
| `ADMIN_PASSWORD` | Strong unique password | If missing, default (`admin123`, `admin`, etc.), **admin routes fail closed (return 404)**. |
| `LLM_API_KEY` | Valid Gemini API Key | Required for LLM extraction and consultative scoping. |
| `LLM_MODEL` | `gemini-2.5-flash` or `gemini-3.8-flash` | LLM model engine source of truth. |
| `EMBEDDING_BACKEND` | `gemini` | Embeds documents and queries with 768-dim vectors. |
| `CORS_ORIGINS` | Comma-separated domains | Explicit origins (e.g. `https://dummy-web-portal-ten.vercel.app,https://nexus-presales-bot-sales.vercel.app`). Wildcard `*` raises `ValueError`. |

---

## 5. Demo Escape Hatch (`ALLOW_EPHEMERAL_DB=true`)

For temporary preview deployments, staging demonstrations, or zero-cost tests without a PostgreSQL database:

```env
ALLOW_EPHEMERAL_DB=true
```

### Limitations & Trade-offs:
1. **Ephemeral Persistence**: Uses SQLite in `/tmp/presales.db`. All chat sessions, leads, bookings, and tokens are lost whenever the serverless container restarts or cycles.
2. **Lazy First-Request Ingest**: Runs on the first database call under a lock with a **20-second time budget**. Partial progress is saved if the budget expires.
3. **Audit Visibility**: The server logs an `ERROR` on startup:
   `"EPHEMERAL DATABASE: sessions, bookings and handoffs will be lost"`, and reports `"persistence": "ephemeral"` in the authenticated admin health endpoint (`/admin/api/health`).
