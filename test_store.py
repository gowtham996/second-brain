from app.db import store_document

# Store a test note
count = store_document(
    content="LangGraph is a library for building stateful multi-agent applications with LLMs. It uses a graph structure with nodes and edges.",
    source_type="note",
    source_name="test note",
    title="LangGraph basics"
)

print(f"✓ Stored {count} chunk(s)")