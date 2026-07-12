import os
from dotenv import load_dotenv
from sqlalchemy import create_engine, text

load_dotenv()

engine = create_engine(os.getenv("DATABASE_URL"))

# ── Create the documents table ────────────────────────────────
# This table stores every chunk of knowledge you add
create_table_sql = """
CREATE TABLE IF NOT EXISTS documents (
    id           BIGSERIAL PRIMARY KEY,
    content      TEXT NOT NULL,           -- the chunk text
    embedding    VECTOR(384),             -- the 384-number vector
    source_type  TEXT,                    -- 'pdf', 'web', 'note'
    source_name  TEXT,                    -- filename / URL / title
    title        TEXT,                    -- document title
    created_at   TIMESTAMPTZ DEFAULT NOW()  -- when you added it
);
"""

# ── Create an index for fast vector search ────────────────────
# This makes similarity search fast even with thousands of chunks
create_index_sql = """
CREATE INDEX IF NOT EXISTS documents_embedding_idx
ON documents
USING hnsw (embedding vector_cosine_ops);
"""

with engine.connect() as conn:
    conn.execute(text(create_table_sql))
    print("✓ documents table created")

    conn.execute(text(create_index_sql))
    print("✓ vector search index created")

    conn.commit()

print("Schema setup complete")