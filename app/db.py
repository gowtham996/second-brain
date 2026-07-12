import os
from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from fastembed import TextEmbedding
from langchain_text_splitters import RecursiveCharacterTextSplitter

load_dotenv()

# ── Engine — one connection pool for the whole app ────────────
engine = create_engine(os.getenv("DATABASE_URL"))

# ── Embedder — FastEmbed, same model as your RAG API ──────────
# BAAI/bge-small-en-v1.5 outputs 384 numbers → matches VECTOR(384)
embedder = TextEmbedding(model_name="BAAI/bge-small-en-v1.5")

# ── Splitter — breaks long text into chunks ───────────────────
splitter = RecursiveCharacterTextSplitter(
    chunk_size=1000,
    chunk_overlap=200,
    separators=["\n\n", "\n", " "]
)


def embed_text(text_str: str) -> list:
    """Convert one piece of text into a 384-number vector."""
    # FastEmbed returns a generator; we take the first result
    embedding = list(embedder.embed([text_str]))[0]
    return embedding.tolist()


def store_document(content: str, source_type: str,
                   source_name: str, title: str) -> int:
    """
    Chunk the content, embed each chunk, store all chunks
    in the documents table. Returns number of chunks stored.
    """
    # Split into chunks
    chunks = splitter.split_text(content)

    insert_sql = text("""
        INSERT INTO documents 
            (content, embedding, source_type, source_name, title)
        VALUES 
            (:content, :embedding, :source_type, :source_name, :title)
    """)

    with engine.connect() as conn:
        for chunk in chunks:
            vector = embed_text(chunk)
            conn.execute(insert_sql, {
                "content": chunk,
                "embedding": str(vector),  # pgvector accepts string form
                "source_type": source_type,
                "source_name": source_name,
                "title": title
            })
        conn.commit()

    return len(chunks)

def search_documents(query: str, limit: int = 5,
                     source_type: str = None,
                     days_back: int = None) -> list:
    """
    Search stored documents by meaning (vector similarity).
    Optional filters: source_type ('pdf'/'web'/'note') and
    days_back (only docs added in last N days).
    """
    # Embed the query
    query_vector = embed_text(query)

    # Build SQL with optional filters
    # <=> is pgvector's cosine distance operator (smaller = closer)
    sql = """
        SELECT content, source_type, source_name, title, created_at,
               embedding <=> :query_vector AS distance
        FROM documents
        WHERE 1=1
    """
    params = {"query_vector": str(query_vector), "limit": limit}

    # Filter by source type if given
    if source_type:
        sql += " AND source_type = :source_type"
        params["source_type"] = source_type

    # Filter by recency if given
    if days_back:
        sql += " AND created_at >= NOW() - INTERVAL ':days days'".replace(
            ":days", str(int(days_back)))

    # Order by closest match, limit results
    sql += " ORDER BY distance ASC LIMIT :limit"

    with engine.connect() as conn:
        rows = conn.execute(text(sql), params).fetchall()

    # Format results
    results = []
    for row in rows:
        results.append({
            "content": row[0],
            "source_type": row[1],
            "source_name": row[2],
            "title": row[3],
            "created_at": str(row[4]),
            "distance": float(row[5])
        })
    return results

def list_documents() -> list:
    """List all unique documents in the knowledge base."""
    sql = """
        SELECT title, source_type, source_name,
               COUNT(*) AS chunk_count,
               MIN(created_at) AS added_at
        FROM documents
        GROUP BY title, source_type, source_name
        ORDER BY added_at DESC
    """
    with engine.connect() as conn:
        rows = conn.execute(text(sql)).fetchall()

    return [{
        "title": r[0],
        "source_type": r[1],
        "source_name": r[2],
        "chunk_count": r[3],
        "added_at": str(r[4])
    } for r in rows]


def delete_document(source_name: str) -> int:
    """Delete all chunks belonging to one document."""
    sql = "DELETE FROM documents WHERE source_name = :source_name"
    with engine.connect() as conn:
        result = conn.execute(text(sql), {"source_name": source_name})
        conn.commit()
    return result.rowcount