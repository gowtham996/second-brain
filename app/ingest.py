import requests
from bs4 import BeautifulSoup
from langchain_community.document_loaders import PyPDFLoader
from app.db import store_document


# ── Ingest a PDF ──────────────────────────────────────────────
def ingest_pdf(file_path: str, filename: str) -> dict:
    loader = PyPDFLoader(file_path)
    pages = loader.load()

    # Combine all pages into one text block
    full_text = "\n\n".join([page.page_content for page in pages])

    chunks = store_document(
        content=full_text,
        source_type="pdf",
        source_name=filename,
        title=filename.replace(".pdf", "")
    )
    return {"source": filename, "type": "pdf", "chunks_stored": chunks}


# ── Ingest a web article ──────────────────────────────────────
def ingest_web(url: str) -> dict:
    # Fetch the page
    headers = {"User-Agent": "Mozilla/5.0"}  # some sites block bots
    response = requests.get(url, headers=headers, timeout=10)
    response.raise_for_status()

    # Extract readable text
    soup = BeautifulSoup(response.text, "html.parser")

    # Remove script/style tags (junk)
    for tag in soup(["script", "style", "nav", "footer", "header"]):
        tag.decompose()

    # Get the page title
    title = soup.title.string if soup.title else url

    # Get all paragraph text
    paragraphs = soup.find_all("p")
    text_content = "\n\n".join([p.get_text() for p in paragraphs])

    if not text_content.strip():
        # Fallback: get all text if no <p> tags found
        text_content = soup.get_text()

    chunks = store_document(
        content=text_content,
        source_type="web",
        source_name=url,
        title=title.strip()
    )
    return {"source": url, "type": "web", "title": title.strip(),
            "chunks_stored": chunks}


# ── Ingest a plain note ───────────────────────────────────────
def ingest_note(text: str, title: str = "Untitled Note") -> dict:
    chunks = store_document(
        content=text,
        source_type="note",
        source_name=title,
        title=title
    )
    return {"source": title, "type": "note", "chunks_stored": chunks}