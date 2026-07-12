from app.db import search_documents

# Search for something related to what we stored
results = search_documents("what is langgraph used for?", limit=3)

print(f"Found {len(results)} results:\n")
for r in results:
    print(f"Title: {r['title']}")
    print(f"Type: {r['source_type']}")
    print(f"Distance: {r['distance']:.4f}")
    print(f"Content: {r['content'][:100]}...")
    print("---")