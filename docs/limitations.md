# ByteKnights – Known Limitations

## 1. Knowledge Graph Relationships

Knowledge-graph edges are primarily extracted from archive references and links.

An edge therefore indicates that two entities are connected by a reference, but does not necessarily specify a semantic relationship such as:

- membership
- ownership
- alliance
- victory
- location

The retrieved documents must still establish the actual relationship.

## 2. Entity Aliases

Some archive entities appear with capitalization, aliases or title variations.

These may occasionally produce duplicate graph nodes or reduce entity-matching quality.

## 3. Follow-Up Query Noise

The LLM-generated second-hop planner can occasionally produce searches that are broader than necessary.

Filtering is used to remove invalid or placeholder queries, but irrelevant searches may still occur.

## 4. Additional Latency

The graph-assisted pipeline can perform multiple searches for one question.

This improves multi-hop evidence discovery but makes it slower than a simple single-pass vector RAG system.

## 5. Visual Retrieval Heuristics

Visual candidate selection currently relies substantially on archive filenames and question/entity term matching.

This works well when archive images have descriptive filenames, but may be less reliable for poorly named images.

## 6. Vision Model Interpretation

Even when the correct image is retrieved, the vision model may misinterpret small text, symbols or ambiguous visual details.

Visual answers therefore depend on both image retrieval and model interpretation.

## 7. OCR Errors

Tesseract recovered scanned pages that contained no extractable text, but OCR can introduce character or formatting errors on difficult scans.

These errors may influence downstream retrieval.

## 8. Duplicate Formats

Some archive material is available in more than one format, such as PDF and DOCX.

This can result in semantically duplicate evidence appearing in retrieval results.

## 9. Hand-Tuned Retrieval Parameters

Thresholds, candidate counts, entity bonuses and evidence limits were selected during development.

They were not exhaustively optimized against a large independent benchmark.

## 10. Development-Set Evaluation

The system successfully answered all 20 provided development questions during the team's manual evaluation, including all seven primary Track 1B questions.

This result applies only to the provided development set.

It does **not** guarantee equivalent performance on unpublished or unseen evaluation questions.

## 11. External Model Dependency

Final answer generation, search planning and visual interpretation rely on externally hosted models through OpenRouter.

The full system therefore requires:

- Internet connectivity
- A valid API key
- Availability of the selected model/provider

## 12. Local Corpus Path

The development environment uses a locally configured path to the Ashen Era Archive.

A different environment may require updating the corpus path before rebuilding corpus-dependent artifacts.

## 13. Visual Intent Routing

Visual routing currently uses keyword-based intent detection rather than a learned classifier.

Unusually phrased visual questions may therefore be routed incorrectly.

## 14. Graph Alias Duplication

Some semantically identical entities can appear as separate graph nodes because of differences such as capitalization or naming conventions.

This can introduce redundant graph neighbors.

## 15. Scope

The primary engineering focus is **Sub-Track 1B**.

Visual and iterative-search capabilities were implemented as supporting features, but they were not the main optimization target.