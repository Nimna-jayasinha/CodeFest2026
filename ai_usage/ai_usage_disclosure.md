# AI Usage Disclosure

## SLIIT CodeFest 2026 — Sub Track 1B


This document describes how Artificial Intelligence (AI) tools were used during the development of our solution for the SLIIT CodeFest 2026 AI Competition.

## 1. Use of AI Tools

Our team used AI-assisted development tools as a supporting resource throughout the development process.

AI was primarily used for:

- Discussing and understanding the requirements of the multi-document, multi-hop question-answering task.
- Exploring possible RAG architectures and retrieval strategies.
- Understanding the limitations of standard single-hop RAG for questions requiring connections between multiple documents.
- Brainstorming approaches for multi-hop retrieval, query expansion, evidence selection, and retrieval evaluation.
- Generating implementation suggestions and code scaffolding for experimental components.
- Assisting with debugging and identifying potential implementation issues.
- Improving code organization, modularity, documentation, and readability.
- Suggesting evaluation strategies and metrics for comparing the baseline RAG system with the multi-hop versions.

## 2. AI-Assisted Development in Our System

AI assistance was used during the development of our retrieval pipeline, including experimentation with:

1. A standard baseline RAG pipeline using the provided document chunks and FAISS index.
2. A multi-hop retrieval pipeline in which:
   - The original question is used for first-hop retrieval.
   - Retrieved evidence is analyzed for relevant entities and relationships.
   - Targeted follow-up queries are generated.
   - The follow-up queries are used for additional FAISS retrieval.
   - Evidence from the different retrieval stages is combined before answer generation.
3. Evidence filtering techniques including:
   - Deduplication.
   - Similarity-score filtering.
   - Source diversity constraints.
   - Maximum evidence limits.

AI assistance was also used to help structure these components as separate modules so that different approaches could be evaluated against the original baseline.

## 3. Human Responsibility and Decision Making

AI-generated suggestions and code were not accepted without review.

Our team was responsible for:

- Inspecting and understanding the competition dataset and document structure.
- Deciding which retrieval architecture to investigate.
- Selecting the baseline and multi-hop approaches to implement.
- Determining retrieval parameters and filtering strategies.
- Testing the implementations against the competition questions.
- Identifying retrieval failures and irrelevant evidence.
- Evaluating whether retrieved evidence was sufficient to answer multi-hop questions.
- Modifying, integrating, testing, and validating AI-assisted code.
- Making the final technical decisions regarding the system architecture and implementation.

AI tools were therefore used as development and reasoning assistants rather than as autonomous decision-makers.

## 4. Validation of AI-Assisted Code

All AI assisted implementation was reviewed and tested by the team before being incorporated into the project.

Particular attention was given to:

- Correct use of the existing FAISS index.
- Compatibility with the existing document chunks and metadata.
- Preservation of the baseline implementation for comparison.
- Retrieval recall and evidence quality.
- Prevention of duplicate evidence.
- Avoiding excessive filtering that could remove important low-similarity evidence.
- Maintaining provenance of retrieved evidence.
- Runtime and implementation complexity.

The team used experimental results to determine whether suggested approaches were actually beneficial rather than relying solely on AI-generated recommendations.

## 5. Transparency

AI assistance contributed to parts of the development and experimentation process, including code generation, technical discussion, debugging, documentation, and design exploration.

However, the final system represents the team's own implementation, testing, evaluation, and technical decisions. AI-generated content was reviewed, adapted, and integrated by the team according to the requirements of the competition.

## 6. AI Tools Used

The primary AI tool used during development was:

- **ChatGPT** , **Claude** - used for technical discussion, architecture exploration, implementation assistance, debugging, documentation, and evaluation planning.

No claim is made that AI independently designed, implemented, tested, or validated the complete competition solution.

---

**Declaration:**  
We confirm that the above information accurately describes the role of AI-assisted tools in the development of our SLIIT CodeFest 2026 submission.