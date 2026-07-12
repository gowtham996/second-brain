import os
from dotenv import load_dotenv
from sqlalchemy import create_engine, text

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

# Connect
engine = create_engine(DATABASE_URL)

with engine.connect() as conn:
    # Test 1: basic connection
    result = conn.execute(text("SELECT version()"))
    print("Connected to:", result.fetchone()[0][:50])

    # Test 2: check pgvector is enabled
    result = conn.execute(text(
        "SELECT * FROM pg_extension WHERE extname = 'vector'"
    ))
    if result.fetchone():
        print("✓ pgvector extension is enabled")
    else:
        print("✗ pgvector NOT enabled — enable it in Supabase")

print("Database test complete")