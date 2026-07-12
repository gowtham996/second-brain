from app.db import search_documents
results = search_documents("how does retrieval augmented generation work?", limit=3)
for r in results:
    print(r['title'], "|", r['source_type'], "|", f"{r['distance']:.3f}")