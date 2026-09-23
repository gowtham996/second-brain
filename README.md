# Second Brain

A personal knowledge assistant. Save PDFs, web articles, and notes into a Postgres/pgvector store, then search them by meaning or ask questions that get answered by synthesizing across everything you've saved.

## How it works

1. **Ingest** — PDFs, web pages, and plain notes are chunked and embedded (`BAAI/bge-small-en-v1.5`, 384-dim, via FastEmbed) and stored in Postgres with `pgvector`.
2. **Search** — semantic (cosine similarity) search over stored chunks, with optional filters by source type and recency.
3. **Ask** — a small [LangGraph](https://github.com/langchain-ai/langgraph) agent retrieves the most relevant chunks and asks Groq's Llama 3.3 70B to synthesize them into one coherent answer, citing which saved sources it used.

## Setup

Requirements:
- Python 3.11
- A Postgres database with the `pgvector` extension enabled (e.g. [Supabase](https://supabase.com))
- A [Groq](https://console.groq.com) API key

```bash
python -m venv venv
venv\Scripts\activate        # Windows
# source venv/bin/activate   # macOS/Linux

pip install -r requirements.txt
```

Create a `.env` file in the project root:

```
DATABASE_URL=postgresql://...
GROQ_API_KEY=...
```

Create the database schema (run once, safe to re-run):

```bash
python schema.py
```

Run the API:

```bash
uvicorn app.main:app --reload
```

The UI is served at `http://localhost:8000/`.

## API

| Endpoint | Method | Description |
|---|---|---|
| `/add/pdf` | POST | Upload a PDF file (multipart form) |
| `/add/web` | POST | Ingest a web article by URL (`{"url": "..."}`) |
| `/add/note` | POST | Save a plain text note (`{"text": "...", "title": "..."}`) |
| `/search` | POST | Vector search (`{"query": "...", "limit": 5, "source_type": null, "days_back": null}`) |
| `/ask` | POST | Ask a question, get a synthesized answer (`{"question": "...", "source_type": null, "days_back": null}`) |
| `/documents` | GET | List all stored documents |
| `/documents?source_name=...` | DELETE | Delete a document and all its chunks |

## Manual test scripts

There's no automated test suite; the root-level `test_*.py` files are standalone scripts that exercise the DB/API directly against a live database:

```bash
python test_db.py       # verify DB connectivity + pgvector extension
python test_store.py    # store a sample note
python test_search.py   # run a sample vector search
python test_web.py      # ingest a real URL end-to-end
```

## Deployment

Deploys to [Render](https://render.com) as a single web service via `render.yaml`. Set `DATABASE_URL` and `GROQ_API_KEY` in the Render dashboard.

## Tech stack

FastAPI · LangGraph · LangChain · Groq (Llama 3.3 70B) · FastEmbed · PostgreSQL + pgvector · SQLAlchemy
