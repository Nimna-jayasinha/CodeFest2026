# ByteKnights – Technical Decisions

## 1. Primary Focus: Sub-Track 1B

The team selected **Sub-Track 1B – Connecting Facts Across Thousands of Pages** as the primary focus.

The main technical challenge is not simply retrieving a relevant document, but connecting facts distributed across multiple archive sources.

Therefore, the system was designed around multi-hop retrieval rather than single-pass RAG.

## 2. Baseline Before Complexity

Development began with a simple vector RAG baseline:

```text
Question → Embedding → FAISS → Evidence → LLM
```

This provided a working reference point before graph and multi-hop components were introduced.

This incremental approach made failures easier to identify and debug.

## 3. SentenceTransformer Embeddings

The system uses:

`sentence-transformers/all-MiniLM-L6-v2`

This model was selected because it provides relatively lightweight semantic embeddings suitable for local development.

Embeddings are normalized before indexing.

## 4. FAISS for Vector Retrieval

FAISS `IndexFlatIP` was selected for vector search.

The corpus size is manageable enough that an exact flat index provides sufficient retrieval performance without requiring a more complex approximate index.

## 5. Candidate Expansion Before Reranking

Instead of retrieving only the final required number of chunks, FAISS retrieves a larger candidate pool.

This was introduced because relevant evidence could otherwise be ranked just outside the initial top-k results.

The larger candidate set gives the entity-aware reranker an opportunity to recover such evidence.

## 6. Entity-Aware Reranking

Semantic similarity occasionally confused related or similarly named archive entities.

Entity-aware bonuses were therefore added for exact entity matches in source names and chunk text.

This combines semantic similarity with explicit entity relevance.

## 7. Knowledge Graph as Retrieval Support

The archive's Markdown links provide useful entity connectivity.

A lightweight NetworkX graph was built from these references.

The graph is used to discover potentially useful neighboring entities for additional retrieval.

It is intentionally treated as a **retrieval-expansion graph**, not a fully typed semantic knowledge graph.

## 8. LLM-Assisted Second-Hop Planning

Fixed retrieval queries are insufficient for every possible relationship chain.

An LLM is therefore used to generate targeted follow-up searches based on:

- Original question
- First-hop evidence
- Detected entities
- Graph neighbors

The LLM does not directly determine the final factual answer during this stage. Its role is to help identify what should be searched next.

## 9. Stage-Aware Evidence Fusion

Simply sorting every retrieved chunk by one global score caused useful later-hop evidence to be lost.

Evidence fusion therefore preserves results from:

- First-hop retrieval
- Graph-guided retrieval
- Second-hop retrieval

This increases the chance that the final LLM receives the complete reasoning chain.

## 10. Source Diversification

A maximum number of chunks per source is used during retrieval stages.

This prevents a single large document from dominating the evidence context and encourages evidence from multiple archive sources.

## 11. Relationship Integrity

Multi-hop questions frequently depend on the exact meaning of relationships.

The final answer prompt explicitly distinguishes relationships such as:

```text
member of
allied with
associated with
participated in
won
```

This reduces incorrect conclusions caused by treating loosely related facts as equivalent.

## 12. Separate Visual Pipeline

Visual questions are not answered by attempting to infer visual details from surrounding text.

Instead, they are routed to a separate pipeline that retrieves the actual archive image and provides it to a vision-capable model.

This avoids unsupported text-based guesses about visual evidence.

## 13. OCR Only Where Needed

OCR is applied to records where normal PDF extraction produced no text.

This avoids unnecessary OCR processing while recovering scanned archive material.

## 14. Preserve the Original Corpus

The Ashen Era Archive is treated as read-only.

Processed records, chunks, indexes, OCR output and graph artifacts are written to separate project directories.

## 15. Streamlit for Demonstration

Streamlit was selected for the final interface because it provides a lightweight way to demonstrate:

- Question entry
- Automatic pipeline routing
- Final answers
- Text evidence
- Page information
- Visual evidence

This allowed development effort to remain focused on retrieval quality rather than frontend complexity.

## 16. Development Philosophy

The system was developed incrementally:

```text
Extraction
→ OCR
→ Chunking
→ Vector RAG
→ Entity Reranking
→ Multi-Hop Retrieval
→ Knowledge Graph
→ Evidence Fusion
→ Visual Retrieval
→ Unified UI
```

Each major capability was tested before the next layer was introduced.