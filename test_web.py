from app.ingest import ingest_web

# Try a real article
result = ingest_web("https://en.wikipedia.org/wiki/Retrieval-augmented_generation")
print(result)