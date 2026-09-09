# Project Context

## Project

**SLIIT CodeFest 2026 — AI Competition**  
**Sub Track 1B: Connecting Facts Across Thousands of Pages**

Our project is an intelligent document question-answering system designed to answer questions over the **Ashen Era Archive**, a corpus containing interconnected documents.

The key challenge is that some questions cannot be answered from a single document or chunk. The required answer may depend on connecting facts across multiple documents.

For example, a question may require a chain such as:

```text
Person
  ↓
Faction / Organization
  ↓
Event / Agreement / Accord
  ↓
Final Answer
```

Therefore, retrieving a highly similar document for the original question is not always sufficient.

---

## Dataset

The system operates on the provided **Ashen Era Archive corpus**.

The corpus is treated as a collection of interconnected documents and pre-existing document chunks. Chunks contain textual evidence and associated metadata such as source/document information.

The project uses the provided/prepared document chunks and FAISS vector index for semantic retrieval.

Important dataset characteristics for this project include:

- Multiple documents may describe related entities.
- Important facts may be distributed across different documents.
- Some documents may contain overlapping or duplicated information.
- A relevant fact may appear in a chunk that has relatively low similarity to the original question.
- Relationships between entities may need to be discovered incrementally.

Because of this, retrieval quality must be evaluated in terms of **evidence recall**, not only similarity scores.

---

## Current System Evolution

The project is being developed incrementally so that each improvement can be compared against previous versions.

### 1. Baseline RAG

The initial system performs a standard single-step retrieval process:

```text
Question
   ↓
FAISS Vector Search
   ↓
Top-K Chunks
   ↓
Context Construction
   ↓
LLM
   ↓
Answer
```

The baseline is intentionally kept available so that improvements can be measured against it.

---

### 2. Two-Hop Multi-Hop RAG

The next version extends the baseline rather than replacing FAISS.

```text
Question
   ↓
Hop 1 FAISS Retrieval
   ↓
First-Hop Evidence
   ↓
Entity / Relationship Identification
   ↓
Targeted Follow-Up Queries
   ↓
Hop 2 FAISS Retrieval
   ↓
Combined Evidence
   ↓
LLM
   ↓
Answer
```

The first hop retrieves evidence related to the original question.

The retrieved evidence is then analyzed to identify useful entities and relationships that may require further investigation.

Targeted follow-up queries are generated from the first-hop evidence and used to perform additional searches against the **same FAISS index**.

The resulting evidence from both hops is provided to the final LLM.

The current implementation intentionally uses a limited two-hop process rather than an unrestricted recursive agent loop.

---

## Evidence Filtering

The multi-hop pipeline was further improved after observing that correct evidence was being retrieved together with irrelevant documents.

The current evidence-control stage applies four techniques:

### 1. Deduplication

Repeated chunks are removed using their chunk identifiers.

This prevents the same evidence from appearing multiple times when it is retrieved through different hops or follow-up queries.

### 2. Similarity Score Filtering

Retrieved evidence can be filtered using a minimum similarity score.

However, similarity filtering must be treated carefully.

A chunk with a lower similarity score may still contain an important bridge fact that connects two entities.

Therefore, the implementation protects the strongest result from Hop 1 and the strongest result from each follow-up query from score filtering.

The purpose is to reduce obvious retrieval noise without unnecessarily damaging multi-hop evidence recall.

### 3. Source Diversity

The number of chunks retained from an individual source document can be limited.

This prevents a single document from dominating the final evidence context when multiple documents are required to answer a question.

This constraint should remain conservative because several chunks from the same document may legitimately contain different required facts.

### 4. Maximum Evidence Limit

A maximum number of evidence chunks can be passed to the final LLM.

This controls context size and reduces the possibility that irrelevant evidence overwhelms useful evidence.

The limit should be tuned experimentally because an overly small limit may remove an important part of a multi-hop evidence chain.

---

## Current Evidence Flow

The current improved pipeline is:

```text
Original Question
       ↓
   Hop 1 FAISS
       ↓
First-Hop Evidence
       ↓
Entity / Relationship Analysis
       ↓
Follow-Up Queries
       ↓
   Hop 2 FAISS
       ↓
Raw Combined Evidence
       ↓
┌─────────────────────────┐
│ Exact Deduplication     │
│ Score Filtering         │
│ Source Diversity        │
│ Maximum Evidence Limit  │
└─────────────────────────┘
       ↓
Filtered Evidence
       ↓
      LLM
       ↓
    Answer
```

Both the **raw evidence** and **filtered evidence** are retained in the multi-hop output so that retrieval quality can be evaluated.

---

## Important Design Principle

The main principle of the project is:

> **Do not optimize only for similarity. Optimize for retaining the evidence chain required to answer the question.**

A low-similarity chunk can be important if it provides the next fact in a multi-hop relationship.

For example:

```text
Question
   ↓
Ederon Fellgard
   ↓
Ashen Vanguard
   ↓
Relevant Accord
```

The chunk describing the accord may not mention Ederon Fellgard directly.

Consequently, its similarity to the original question could be lower even though it is essential to the final answer.

---

## Evaluation

The system should be evaluated progressively rather than only by final answer quality.

Important evaluation measures include:

### Retrieval

- Hop-1 Recall@K
- Hop-2 Recall@K
- Raw evidence recall
- Filtered evidence recall

### Evidence Quality

- Relevant evidence count
- Irrelevant evidence count
- Duplicate evidence count
- Source diversity
- Evidence retained after filtering

### Answering

- Final answer accuracy
- Whether all required facts are supported by retrieved evidence
- Whether the answer correctly connects facts across documents

### Efficiency

- Number of FAISS searches
- Retrieval latency
- Query expansion latency
- Total response latency
- Final context size

---

## Baseline Comparison

The original baseline must remain available for controlled comparison.

### Baseline

```text
Question
   ↓
FAISS
   ↓
Top-K
   ↓
LLM
```

### Multi-Hop

```text
Question
   ↓
FAISS
   ↓
Query Expansion
   ↓
FAISS
   ↓
Combined Evidence
   ↓
LLM
```

### Filtered Multi-Hop

```text
Question
   ↓
FAISS
   ↓
Query Expansion
   ↓
FAISS
   ↓
Evidence Filtering
   ↓
LLM
```

This progression allows the team to determine whether improvements come from multi-hop retrieval, evidence filtering, or both.

---

## Current Implementation Constraints

The current experimental system should preserve the following constraints:

- Keep the original baseline implementation available.
- Continue using FAISS as the vector retrieval system.
- Reuse the existing document chunks and FAISS index.
- Keep the multi-hop pipeline modular.
- Do not introduce unrestricted recursive agent reasoning.
- Do not introduce a graph database unless explicitly decided later.
- Preserve retrieval provenance and chunk metadata.
- Record raw evidence before filtering whenever possible.
- Evaluate recall before aggressively increasing filtering.
- Avoid assuming that the highest similarity score represents the most important evidence.

---

## Repository Structure

The main experimental components are organized approximately as follows:

```text
project/
│
├── main.py
├── rag.py
├── retriever.py
├── generator.py
├── context.py
├── config.py
│
├── multihop.py
├── multihop_main.py
│
├── data/
│   └── document chunks
│
├── index/
│   └── FAISS index
│
├── README.md
├── README_MULTIHOP.md
├── AI_USAGE_DISCLOSURE.md
└── context.md
```

The exact repository structure may contain additional files.

---

## Development Philosophy

The system is being developed experimentally.

Rather than assuming that a more complicated architecture will automatically perform better, each stage is evaluated against the previous version.

The intended progression is:

```text
Dataset Understanding
        ↓
Baseline RAG
        ↓
Two-Hop Retrieval
        ↓
Evidence Filtering
        ↓
Evaluation
        ↓
Identify Remaining Bottlenecks
        ↓
Further Improvements
```

The main objective is to improve the system's ability to **retrieve and connect distributed evidence across the Ashen Era Archive while maintaining high evidence recall and controlling irrelevant context**.
