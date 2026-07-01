from pathlib import Path

import chromadb
import voyageai
from dotenv import find_dotenv, load_dotenv

load_dotenv(find_dotenv())

# --- Config ---

DATA_DIR = Path(__file__).parent / "data"
CHROMA_PATH = DATA_DIR / "chroma"
COLLECTION_NAME = "regulatory_docs"
EMBED_MODEL = "voyage-3-large"
TOP_K = 5
SIMILARITY_THRESHOLD = 0.5


# --- Retrieval ---

def retrieve(
    question: str,
    top_k: int = TOP_K,
    threshold: float = SIMILARITY_THRESHOLD,
) -> list[dict]:
    """
    Embeds a question and retrieves the most semantically similar chunks
    from ChromaDB, filtered by a cosine distance threshold.

    Parameters
    ----------
    question  : The natural-language question to retrieve context for.
    top_k     : Maximum number of chunks to retrieve before threshold filtering.
    threshold : Maximum cosine distance a chunk may have from the query and
                still be returned.
                Cosine distance 0.0 = identical vectors,
                1.0 = orthogonal, 2.0 = opposite.

    Returns
    -------
    List of chunk dicts, each containing:
        id       : chunk identifier — passed to generate.py for citation validation
        text     : cleaned section body — inserted into the generation prompt
        metadata : source filename and section title — used for citation display
        distance : cosine distance from query vector — useful for threshold tuning
    """
    vo = voyageai.Client()
    client = chromadb.PersistentClient(path=str(CHROMA_PATH))

    collection = client.get_or_create_collection(
        name=COLLECTION_NAME,
        metadata={"hnsw:space": "cosine"},
        embedding_function=None,
    )

    query_embedding = vo.embed(
        [question],
        model=EMBED_MODEL,
        input_type="query",
    ).embeddings[0]

    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=top_k,
        include=["documents", "metadatas", "distances"],
    )

    ids = results["ids"][0]
    documents = results["documents"][0]
    metadatas = results["metadatas"][0]
    distances = results["distances"][0]

    chunks = []
    for chunk_id, text, metadata, distance in zip(ids, documents, metadatas, distances):
        if distance > threshold:
            continue
        chunks.append({
            "id": chunk_id,
            "text": text,
            "metadata": metadata,
            "distance": round(distance, 4),
        })
    return chunks


if __name__ == "__main__":
    test_questions = [
        "What are the key principles for data aggregation under BCBS 239?",
        "What are the PRA's requirements for model validation?",
        "What does BCBS 239 say about data lineage?",
        "What risks does the Bank of England identify for AI in financial services?",
        "What is the capital of France?",
    ]

    for question in test_questions:
        print(f"\nQ: {question}")
        chunks = retrieve(question)
        if not chunks:
            print("  → No chunks above threshold (unanswerable)")
        else:
            for c in chunks:
                print(f"  [{c['distance']}] {c['metadata']['source']} — {c['metadata']['section'][:60]}")