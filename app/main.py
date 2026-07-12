import os
import shutil
import time
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel

from app.ingest import ingest_pdf, ingest_web, ingest_note
from app.db import search_documents, list_documents, delete_document
from app.agent import ask_brain

app = FastAPI(title="Second Brain API")

UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)


# ── Request models ────────────────────────────────────────────
class WebRequest(BaseModel):
    url: str


class NoteRequest(BaseModel):
    text: str
    title: str = "Untitled Note"


class SearchRequest(BaseModel):
    query: str
    limit: int = 5
    source_type: str = None   # optional: 'pdf' / 'web' / 'note'
    days_back: int = None     # optional: last N days


class AskRequest(BaseModel):
    question: str
    source_type: str = None
    days_back: int = None


# ── Ingestion endpoints ───────────────────────────────────────
@app.post("/add/pdf")
async def add_pdf(file: UploadFile = File(...)):
    if not file.filename.endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files allowed")

    file_path = f"{UPLOAD_DIR}/{file.filename}"
    with open(file_path, "wb") as f:
        shutil.copyfileobj(file.file, f)

    result = ingest_pdf(file_path, file.filename)
    return result


@app.post("/add/web")
async def add_web(request: WebRequest):
    try:
        result = ingest_web(request.url)
        return result
    except Exception as e:
        raise HTTPException(
            status_code=400,
            detail=f"Failed to fetch URL: {str(e)}"
        )


@app.post("/add/note")
async def add_note(request: NoteRequest):
    result = ingest_note(request.text, request.title)
    return result


# ── Search endpoint ───────────────────────────────────────────
@app.post("/search")
async def search(request: SearchRequest):
    start = time.time()
    results = search_documents(
        query=request.query,
        limit=request.limit,
        source_type=request.source_type,
        days_back=request.days_back
    )
    latency_ms = round((time.time() - start) * 1000)
    return {
        "query": request.query,
        "results": results,
        "count": len(results),
        "latency_ms": latency_ms
    }


# ── Ask endpoint (synthesis agent) ────────────────────────────
@app.post("/ask")
async def ask(request: AskRequest):
    start = time.time()
    result = ask_brain(
        question=request.question,
        source_type=request.source_type,
        days_back=request.days_back
    )
    result["latency_ms"] = round((time.time() - start) * 1000)
    return result


# ── Document management ───────────────────────────────────────
@app.get("/documents")
async def get_documents():
    docs = list_documents()
    return {"documents": docs, "count": len(docs)}


@app.delete("/documents")
async def remove_document(source_name: str):
    deleted = delete_document(source_name)
    return {"deleted_chunks": deleted, "source": source_name}


# ── Serve the UI (must stay last) ─────────────────────────────
@app.get("/")
def serve_ui():
    return FileResponse("static/index.html")