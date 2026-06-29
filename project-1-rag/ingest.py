import json
import re
from pathlib import Path

import chromadb
import pymupdf4llm
import voyageai
from dotenv import find_dotenv, load_dotenv

load_dotenv(find_dotenv())

# --- Config ---

DATA_DIR = Path(__file__).parent / "data"
CHUNKS_OUTPUT = DATA_DIR / "chunks.jsonl"
CHROMA_PATH = DATA_DIR / "chroma"
COLLECTION_NAME = "regulatory_docs"

MIN_CHUNK_CHARS = 100
EMBED_MODEL = "voyage-3-large"
BATCH_SIZE = 128    # Voyage AI max texts per request


# --- Chunking ---

def chunk_by_section(document_text: str) -> list[dict]:
    """
    Splits markdown text into sections using heading markers (## / ### / ####).

    Splits on levels 2-4 only:
      - Level 1 (#) is the document title — treated as preamble, not a boundary.
      - Levels 2-4 map to real sections and subsections.
      - Level 5+ (#####) are pull quotes or callouts in some PDFs — ignored.

    pymupdf4llm assigns heading levels based on font size, so this reliably
    identifies document sections without hardcoding document-specific patterns.
    """
    pattern = re.compile(r"\n(?=#{2,4} )")
    raw_chunks = pattern.split(document_text)
    sections = []
    for chunk in raw_chunks:
        chunk = chunk.strip()
        if not chunk:
            continue
        lines = chunk.splitlines()
        heading_line = lines[0].lstrip("#").strip()
        body = "\n".join(lines[1:]).strip()
        sections.append({"title": heading_line, "content": body})
    return sections


# --- PDF processing ---

def clean_text(text: str) -> str:
    """
    Removes PDF/markdown artefacts that add noise for embedding.

    Strips HTML superscript tags (footnote references), bold/italic markdown
    syntax, and collapses runs of blank lines to a single blank line.
    """
    text = re.sub(r"<sup>.*?</sup>", "", text)           # strip footnote superscripts
    text = re.sub(r"\*{1,2}(.+?)\*{1,2}", r"\1", text)  # strip bold/italic markdown
    text = re.sub(r"\n{3,}", "\n\n", text)               # collapse excessive blank lines
    return text.strip()


def make_chunk_id(filename_stem: str, title: str, index: int) -> str:
    """
    Builds a stable, unique ID for a chunk in the format:
        {filename_stem}__{section_slug}__{index}

    The index acts as a tiebreaker when the same section title appears more
    than once in a document. Deterministic IDs allow vector DB upserts on
    reprocessing rather than creating duplicates.
    """
    slug = re.sub(r"[^a-z0-9]+", "_", title.lower()).strip("_")
    return f"{filename_stem}__{slug}__{index}"


def process_pdf(pdf_path: Path) -> list[dict]:
    """
    Converts a PDF to markdown, chunks by section, cleans text, and returns
    a list of chunk dicts ready for embedding.

    Uses pymupdf4llm for conversion — it uses font size metadata to assign
    markdown heading levels, making section detection reliable across different
    PDF layouts without document-specific heuristics.

    Each returned dict contains:
        id:       stable unique identifier (filename + section + index)
        text:     cleaned section body for embedding
        metadata: source filename and section title for retrieval attribution
    """
    markdown = pymupdf4llm.to_markdown(str(pdf_path))
    raw_sections = chunk_by_section(markdown)
    chunks = []
    for i, section in enumerate(raw_sections):
        text = clean_text(section["content"])
        if len(text) < MIN_CHUNK_CHARS:
            continue
        chunks.append({
            "id": make_chunk_id(pdf_path.stem, section["title"], i),
            "text": text,
            "metadata": {
                "source": pdf_path.name,
                "section": clean_text(section["title"]),
            },
        })
    return chunks


# --- Embedding ---

def embed_chunks(vo: voyageai.Client, chunks: list[dict], model: str = EMBED_MODEL) -> list[dict]:
    """
    Embeds a list of chunk dicts using Voyage AI and returns them with an
    added 'embedding' key containing the vector (list of floats).

    Sends texts in batches of BATCH_SIZE (128, the Voyage AI maximum per request).
    input_type='document' produces vectors optimised for retrieval storage
    rather than query matching (use input_type='query' at search time).
    """
    texts = [c["text"] for c in chunks]
    embeddings = []
    for i in range(0, len(texts), BATCH_SIZE):
        batch = texts[i : i + BATCH_SIZE]
        result = vo.embed(batch, model=model, input_type="document")
        embeddings.extend(result.embeddings)
        print(f"  Embedded {min(i + BATCH_SIZE, len(texts))}/{len(texts)}")
    for chunk, vector in zip(chunks, embeddings):
        chunk["embedding"] = vector
    return chunks


# --- ChromaDB ingestion ---

def ingest_into_chroma(chunks: list[dict]) -> None:
    """
    Ingests pre-embedded chunks into a ChromaDB persistent collection.

    Uses a persistent client so the collection survives between runs without
    re-embedding. get_or_create_collection is idempotent — safe to call on
    reruns — but adding duplicate IDs will raise; delete the collection first
    if reprocessing from scratch.

    hnsw:space='cosine' is set explicitly because Voyage AI embeddings are
    designed for cosine similarity, not the default L2 distance.
    """
    client = chromadb.PersistentClient(path=str(CHROMA_PATH))
    collection = client.get_or_create_collection(
        name=COLLECTION_NAME,
        metadata={"hnsw:space": "cosine"},
    )
    collection.add(
        ids=[c["id"] for c in chunks],
        embeddings=[c["embedding"] for c in chunks],
        documents=[c["text"] for c in chunks],
        metadatas=[c["metadata"] for c in chunks],
    )
    print(f"Ingested {collection.count()} documents into '{COLLECTION_NAME}' at {CHROMA_PATH}")


# --- Pipeline ---

def main() -> None:
    # 1. Convert all PDFs in data/ to chunks
    all_chunks = []
    for pdf_path in sorted(DATA_DIR.glob("*.pdf")):
        chunks = process_pdf(pdf_path)
        all_chunks.extend(chunks)
        print(f"{pdf_path.name}: {len(chunks)} chunks")
    print(f"\nTotal chunks: {len(all_chunks)}")

    # 2. Save raw chunks to JSONL before embedding (decouples parsing from embedding)
    with CHUNKS_OUTPUT.open("w", encoding="utf-8") as f:
        for chunk in all_chunks:
            f.write(json.dumps(chunk) + "\n")
    print(f"Saved chunks to {CHUNKS_OUTPUT}")

    # 3. Embed chunks with Voyage AI
    vo = voyageai.Client()
    all_chunks = embed_chunks(vo, all_chunks)
    print(f"\nEmbedding complete — {len(all_chunks)} chunks")

    # 4. Ingest into ChromaDB
    ingest_into_chroma(all_chunks)


if __name__ == "__main__":
    main()
