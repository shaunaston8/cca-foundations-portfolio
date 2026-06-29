# Project 1: RAG Knowledge Assistant

A document question-answering system that ingests UK financial regulatory PDFs, indexes them into a local vector store, and answers natural-language queries with structured, cited responses. The system returns an explicit, reasoned refusal when retrieved evidence is insufficient — it does not speculate beyond what the corpus supports.

---

## Corpus

Four publicly available regulatory documents:

| File | Document |
|---|---|
| `pra-ss1-23-model-risk.pdf` | PRA SS1/23 — Model Risk Management Principles for Banks |
| `bcbs-239-rdar.pdf` | BCBS 239 — Principles for Effective Risk Data Aggregation and Risk Reporting |
| `boe-fs2-23-artificial-intelligence-and-machine-learning.pdf` | BoE FS2/23 — Artificial Intelligence and Machine Learning |
| `boe-financial-stability-in-focus-artificial-intelligence.pdf` | BoE Financial Stability in Focus — AI in UK Financial Services |

Domain chosen for professional credibility: all four documents are directly relevant to model risk, data governance, and AI oversight in regulated financial institutions.

---

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     OFFLINE — run once                       │
│                                                             │
│  PDF files                                                  │
│      │                                                      │
│  pymupdf4llm ──► markdown conversion                        │
│      │                                                      │
│  chunk_by_section() ──► List[{id, text, metadata}]          │
│      │                                                      │
│  VoyageAI embed() ──► List[float]  (input_type="document")  │
│      │                                                      │
│  ChromaDB PersistentClient ──► persisted to data/chroma/    │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│                  ONLINE — runs per query                     │
│                                                             │
│  User question (CLI)                                        │
│      │                                                      │
│  retrieve.py                                                │
│    ├─ VoyageAI embed() (input_type="query")                 │
│    ├─ ChromaDB collection.query() top-k=5                   │
│    └─ cosine distance threshold gate (≤ 0.5)                │
│      │                                                      │
│      ├── empty → RAGResponse(answerable=False)              │
│      │                                                      │
│  generate.py                                                │
│    ├─ format chunks with explicit IDs into prompt           │
│    ├─ Claude via tool_choice forced extraction              │
│    └─ validate RAGResponse schema (Pydantic)                │
│      │                                                      │
│  Structured JSON output to terminal                         │
└─────────────────────────────────────────────────────────────┘
```

Ingestion is a one-time offline operation. Re-run only when the corpus changes. The retrieval and generation steps execute on every query.

---

## Key Decisions and Tradeoffs

### 1. Chunking strategy: section-based over fixed-size

**Decision:** Convert PDFs to markdown via `pymupdf4llm`, then split on heading markers (`##`, `###`, `####`).

**Rationale:** Regulatory documents are authored to be navigated by section. A question about model validation governance maps to a specific numbered section in SS1/23; a question about data lineage maps to a specific BCBS 239 principle. Fixed-size chunking would routinely split those sections mid-argument and force the retrieval layer to reconstruct coherence from fragments. Section-based chunking preserves the semantic unit the document author intended.

**Heading levels 2–4 only:** Level 1 (`#`) is the document title and is treated as preamble rather than a section boundary. Levels 5+ (`#####`) are pull-quote callouts in some BoE reports and are not meaningful retrieval units. This was confirmed empirically: restricting to levels 2–4 increased BCBS 239 from 19 to 44 chunks and BoE Financial Stability from 7 to 13 chunks by correctly detecting sub-principle structure that was being missed at level 1 only.

**Trade-off accepted:** Quality dependency shifts from chunking logic to conversion fidelity. Fixed-size chunking is more robust to poor PDF conversion output; section-based chunking rewards good conversion and degrades more sharply on documents with non-typographic structure. This trade-off is acceptable for this corpus because all four documents are published regulatory texts with consistent heading hierarchies.

**What would change this decision:** Unstructured source documents — earnings call transcripts, free-form internal memos, scanned documents without typographic hierarchy — where no reliable section boundaries exist. The `chunk_by_char` and `chunk_by_sentence` functions are retained in `ingest.py` as documented fallback strategies for exactly this case.

---

### 2. Embedding: VoyageAI with asymmetric input types

**Decision:** VoyageAI `voyage-3-large` for embedding, with `input_type="document"` at ingestion time and `input_type="query"` at retrieval time.

**Rationale:** VoyageAI produces domain-optimised dense embeddings. The asymmetric input type distinction matters: VoyageAI optimises the vector representation differently depending on whether the text is a document to be stored or a question to be matched against stored documents. Using `"document"` for queries, or omitting the parameter entirely, measurably degrades retrieval quality.

**Trade-off accepted:** VoyageAI requires an external API call and account. ChromaDB's default sentence-transformers model (`all-MiniLM-L6-v2`) would run entirely locally with no external dependency, but is a general-purpose model not optimised for financial or legal prose. For production use over this corpus, domain-specific embedding quality is worth the external dependency.

**What would change this decision in production:** `voyage-finance-2` is VoyageAI's specialised model for financial domain text. It was not used here because the general `voyage-3-large` model is sufficient to demonstrate the architecture, but `voyage-finance-2` would be the correct production choice for a regulatory document retrieval system.

---

### 3. Vector store: ChromaDB local PersistentClient

**Decision:** ChromaDB running locally as a file-persisted store, with `hnsw:space="cosine"` set explicitly.

**Rationale:** ChromaDB in `PersistentClient` mode requires no account, no infrastructure, and no external service. Embeddings are generated by VoyageAI and passed to ChromaDB explicitly — ChromaDB's built-in embedding function is disabled. This means the two concerns are independently replaceable: changing the embedding model requires no changes to the storage layer, and changing the vector store requires no changes to the embedding logic.

`hnsw:space="cosine"` is set explicitly rather than relying on ChromaDB's default L2 distance, because VoyageAI embeddings are designed for cosine similarity. Using L2 distance on cosine-optimised vectors produces incorrect similarity rankings.

**What would change this decision in production:** A managed vector store — Pinecone, Weaviate, or pgvector — for multi-instance access, horizontal scaling, and operational observability. The embedding/storage separation in this implementation means that migration would require changes only to the `ingest_into_chroma` and `retrieve` functions, not to the embedding or generation layers.

---

### 4. "I don't know" handling: two-layer enforcement

**Decision:** A cosine distance threshold gate in `retrieve.py` as the primary control, plus an explicit refusal instruction in the system prompt as a secondary signal.

**Rationale:** Prompt-level instruction alone is insufficient. A sufficiently confusing retrieved chunk — one that is topically adjacent but not genuinely relevant — can still mislead the model into a confident but wrong answer regardless of system prompt instructions. The threshold gate in `retrieve.py` is a programmatic hard stop: if the best-matching chunk has a cosine distance above 0.5, no chunks are passed to the generation layer and `generate.py` returns `RAGResponse(answerable=False)` without calling Claude at all. This is the concrete application of the principle that **programmatic enforcement takes precedence over prompt-based guidance**.

The system prompt instruction to refuse when evidence is insufficient is retained as a second layer for cases where retrieved chunks pass the threshold but do not actually contain sufficient evidence for the specific question asked.

**Threshold value:** 0.5 cosine distance was chosen empirically against this corpus. Tighten toward 0.3 if irrelevant chunks appear in results; loosen toward 0.7 if legitimate questions trigger refusals.

---

### 5. Hallucinated citation prevention

**Decision:** Chunks are passed to Claude with explicit numbered IDs in the prompt. The `RAGResponse` Pydantic schema requires every citation to reference a `chunk_id`. The generation layer validates that every cited ID exists in the set of IDs passed to that specific call.

**Rationale:** Without this control, Claude will occasionally cite chunk identifiers that were not provided — either hallucinated IDs or IDs from a previous query that were not part of the current retrieved set. Passing chunks with explicit IDs and validating citations against the known set at the application layer is a programmatic enforcement mechanism that makes this failure mode detectable and rejectable at runtime.

**Implementation:** The `model_validator` in `schemas.py` enforces mutual exclusivity between the answerable and refusal response paths at schema validation time, not just as documentation. If Claude returns `answerable=True` with no citations, or `answerable=False` with a populated answer, Pydantic raises a `ValidationError` immediately.

---

## Output Schema

Successful answer:

```json
{
  "answerable": true,
  "answer": "The PRA requires firms to establish a model risk management framework that includes a comprehensive model inventory, independent model validation, and board-level accountability. SS1/23 sets out five core principles governing these requirements.",
  "confidence": "high",
  "citations": [
    {
      "chunk_id": "pra-ss1-23-model-risk__model_validation__12",
      "document_name": "PRA SS1/23 Model Risk Management",
      "page_number": 4,
      "excerpt": "Firms must maintain a comprehensive model inventory covering all models used in material decisions..."
    }
  ],
  "refusal_reason": null
}
```

Refusal:

```json
{
  "answerable": false,
  "answer": null,
  "confidence": null,
  "citations": [],
  "refusal_reason": "The provided documents do not contain information about IFRS 9 expected credit loss model calibration. This topic falls outside the scope of the retrieved context."
}
```

---

## What I Would Change for Production

**Managed vector store.** Replace ChromaDB local persistence with pgvector (if already running Postgres) or Pinecone for multi-instance access, operational monitoring, and index backup. The embedding/storage separation in this implementation means the migration is contained to two functions.

**Domain-specific embedding model.** Replace `voyage-3-large` with `voyage-finance-2` for retrieval accuracy improvements on financial and regulatory prose. All Voyage 4-series models share an embedding space, enabling a cost optimisation: embed documents once with the highest-quality model and use a cheaper model at query time without re-indexing.

**Retrieval evaluation.** Add RAGAS or a lightweight custom evaluator measuring faithfulness (does the answer contradict the retrieved chunks?) and answer relevance (does the answer address the question?). Without evaluation metrics, threshold and k tuning is guesswork.

**Document versioning and incremental re-ingestion.** Track document versions by hash. Re-ingest only documents that have changed rather than dropping and rebuilding the entire collection. `collection.upsert` supports this — the current `collection.add` does not.

**Hybrid retrieval.** Add BM25 lexical search alongside the semantic vector search, merged via Reciprocal Rank Fusion. Semantic search alone misses exact-term matches for defined terms and principle numbers (e.g. "Principle 6" in BCBS 239). Hybrid retrieval recovers these without sacrificing semantic coverage.

**Prompt caching.** The system prompt and chunk formatting are consistent across queries. Adding a `cache_control` breakpoint on the system prompt would reduce latency and cost on repeated queries against the same retrieved chunks.

**Observability.** Log retrieval distances, chunk IDs, and generation latency per query to a structured store. Without this, diagnosing retrieval quality degradation over time is not possible.

---

## Project Structure

```
Project-1-RAG-Knowledge-Assistant/
├── data/
│   ├── *.pdf                  (source regulatory documents)
│   ├── chunks.jsonl           (parsed chunks checkpoint — decouples parsing from embedding)
│   └── chroma/                (ChromaDB persistent store — gitignored)
├── tests/
│   └── test_schemas.py
├── conftest.py
├── ingest.py                  (PDF → markdown → chunks → embeddings → ChromaDB)
├── retrieve.py                (question → embedding → ChromaDB query → threshold gate)
├── generate.py                (chunks → Claude → validated RAGResponse)
├── main.py                    (CLI entry point)
└── schemas.py                 (Pydantic output contract)
```

---

## Setup

```powershell
# From project root
uv add chromadb pymupdf4llm voyageai

# Add to .env
ANTHROPIC_API_KEY=...
VOYAGE_API_KEY=...

# Ingest corpus (one-time)
uv run python Project-1-RAG-Knowledge-Assistant/ingest.py

# Run a query
uv run python Project-1-RAG-Knowledge-Assistant/main.py --question "What are the PRA's requirements for model validation?"
```

---

## Exam Domain Coverage

| Domain | Coverage |
|---|---|
| Prompt Engineering & Structured Output (20%) | Pydantic response schema; tool_choice forced extraction; system prompt design; prefilling patterns |
| Context Management & Reliability (15%) | Two-layer "I don't know" enforcement; threshold gate; citation validation; CALM framework application |