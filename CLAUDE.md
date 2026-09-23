# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

Second Brain: a FastAPI service that ingests PDFs, web articles, and notes into a Postgres/pgvector store, then answers questions over that knowledge base using a LangGraph retrieve→synthesize agent (Groq-hosted Llama 3.3 70B).

## Running locally

```bash
# activate venv first (already created in ./venv)
python schema.py                          # create documents table + hnsw index (idempotent)
uvicorn app.main:app --reload             # run the API, serves static/index.html at /
```

Requires a `.env` with `DATABASE_URL` (Postgres with pgvector extension enabled, e.g. Supabase) and `GROQ_API_KEY`.

There is no test framework configured — `test_*.py` at the repo root are standalone manual scripts (no pytest, no assertions) that hit the live database/API directly, e.g.:

```bash
python test_db.py       # verify DB connectivity + pgvector extension
python test_store.py    # store a sample note
python test_search.py   # run a sample vector search
python test_web.py      # ingest a real URL end-to-end
```

Run these individually as needed; they require a working `DATABASE_URL` (and `test_web.py` needs network access).

## Architecture

Data flow: `app/ingest.py` → `app/db.py` → `app/agent.py`, all wired together in `app/main.py`.

- **app/db.py** — single SQLAlchemy `engine` and FastEmbed `embedder` (`BAAI/bge-small-en-v1.5`, 384-dim) shared across the app. `store_document()` chunks text (1000 chars, 200 overlap) and embeds+inserts each chunk as its own row; there is no separate "documents" vs "chunks" table — every row in `documents` is one chunk, grouped by `source_name`/`title` for display. `search_documents()` does cosine-distance (`<=>`) similarity search with optional `source_type` and `days_back` filters — note `days_back` is interpolated into the SQL string directly (post-`int()`-cast), not bound as a parameter.
- **app/ingest.py** — one function per source type (`ingest_pdf`, `ingest_web`, `ingest_note`), each normalizes its input into plain text and calls `store_document`. Web ingestion strips script/style/nav/footer/header tags and joins `<p>` text, falling back to full-page text if no paragraphs are found.
- **app/agent.py** — a 2-node LangGraph graph (`retrieve` → `synthesize`, `END`). `retrieve` pulls up to 8 chunks via `search_documents`; `synthesize` feeds all chunks in one prompt to Groq Llama 3.3 70B, instructed to produce a single fused answer (not a per-source list) and to name sources it drew from. `ask_brain()` is the sync entry point called by the API.
- **app/main.py** — thin FastAPI layer: `/add/{pdf,web,note}` for ingestion, `/search` for raw vector search, `/ask` for the synthesis agent, `/documents` (GET/DELETE) for management, `/` serves `static/index.html` (must stay the last route since it's a catch-all path).
- **schema.py** — run once (or whenever the schema changes) to create the `documents` table and its HNSW cosine-similarity index. Not imported by the app; it's a standalone setup script.

## Deployment

`render.yaml` deploys as a single Render web service running `uvicorn app.main:app`, pinned to `python-3.11.9` (`runtime.txt`). Required env vars (`GROQ_API_KEY`, `DATABASE_URL`) are set in the Render dashboard, not synced from the repo.
