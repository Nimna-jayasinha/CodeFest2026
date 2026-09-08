from pathlib import Path
import os
import pickle
import json
import re

import faiss
import numpy as np

from dotenv import load_dotenv
from openai import OpenAI
from sentence_transformers import SentenceTransformer


# ============================================================
# CONFIGURATION
# ============================================================

INDEX_FILE = Path("data/index/archive.index")
METADATA_FILE = Path("data/index/chunks.pkl")

EMBEDDING_MODEL = "all-MiniLM-L6-v2"

FIRST_HOP_K = 8
SECOND_HOP_K = 6

MAX_FOLLOW_UP_QUERIES = 3

FIRST_HOP_THRESHOLD = 0.30
SECOND_HOP_THRESHOLD = 0.40

MAX_FINAL_EVIDENCE = 12

# Entity-aware reranking
ENTITY_SOURCE_BOOST = 0.20
ENTITY_TEXT_BOOST = 0.08


# ============================================================
# LOAD API KEY
# ============================================================

load_dotenv()

api_key = os.getenv("OPENROUTER_API_KEY")

if not api_key:
    raise ValueError(
        "OPENROUTER_API_KEY was not found."
    )


client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=api_key
)


# ============================================================
# TEXT NORMALIZATION
# ============================================================

def normalize_text(text):

    if not text:
        return ""

    text = text.lower()

    text = text.replace("_", " ")
    text = text.replace("-", " ")

    text = re.sub(
        r"[^a-z0-9\s]",
        " ",
        text
    )

    text = re.sub(
        r"\s+",
        " ",
        text
    )

    return text.strip()


# ============================================================
# SOURCE / ENTITY NAME
# ============================================================

def source_entity_name(source):

    source = Path(source).stem

    source = source.replace(
        ".scan",
        ""
    )

    return normalize_text(source)


# ============================================================
# ENTITY-AWARE SCORE
# ============================================================

def calculate_entity_boost(
    query,
    result
):

    normalized_query = normalize_text(
        query
    )

    query_word_set = set(
        normalized_query.split()
    )

    source_name = source_entity_name(
        result["source"]
    )

    normalized_document_text = normalize_text(
        result.get("text", "")
    )

    boost = 0.0

    # --------------------------------------------------------
    # 1. Exact source/entity title appears in the query
    # --------------------------------------------------------

    if (
        source_name
        and len(source_name) >= 4
        and source_name in normalized_query
    ):

        boost += ENTITY_SOURCE_BOOST

    # --------------------------------------------------------
    # 2. Important source-title words appear in the query
    # --------------------------------------------------------

    source_words = [
        word
        for word in source_name.split()
        if len(word) >= 5
    ]

    matched_source_words = [
        word
        for word in source_words
        if word in query_word_set
    ]

    if source_words and matched_source_words:

        match_ratio = (
            len(matched_source_words)
            / len(source_words)
        )

        boost += (
            ENTITY_SOURCE_BOOST
            * match_ratio
            * 0.5
        )

    # --------------------------------------------------------
    # 3. Important query terms occur in the chunk text
    # --------------------------------------------------------

    query_words = [
        word
        for word in query_word_set
        if len(word) >= 6
    ]

    text_matches = sum(
        1
        for word in query_words
        if word in normalized_document_text
    )

    if text_matches > 0:

        boost += min(
            ENTITY_TEXT_BOOST,
            text_matches * 0.02
        )

    return boost


# ============================================================
# LOAD SEARCH SYSTEM
# ============================================================

print(
    "Loading ByteKnights "
    "Entity-Aware Multi-Hop RAG V3..."
)

embedding_model = SentenceTransformer(
    EMBEDDING_MODEL
)

index = faiss.read_index(
    str(INDEX_FILE)
)

with open(METADATA_FILE, "rb") as f:
    chunks = pickle.load(f)

print(f"Loaded {len(chunks)} chunks.")
print("System ready.")
print()


# ============================================================
# VECTOR + ENTITY-AWARE SEARCH
# ============================================================

def search(
    query,
    top_k,
    candidate_multiplier=4
):

    # --------------------------------------------------------
    # Create query embedding
    # --------------------------------------------------------

    embedding = embedding_model.encode(
        [query],
        normalize_embeddings=True
    )

    embedding = np.array(
        embedding,
        dtype="float32"
    )

    # --------------------------------------------------------
    # Retrieve MORE candidates than we finally need
    # --------------------------------------------------------

    candidate_k = min(
        top_k * candidate_multiplier,
        len(chunks)
    )

    scores, indices = index.search(
        embedding,
        candidate_k
    )

    results = []

    # --------------------------------------------------------
    # Entity-aware reranking
    # --------------------------------------------------------

    for score, index_id in zip(
        scores[0],
        indices[0]
    ):

        if index_id < 0:
            continue

        chunk = chunks[index_id].copy()

        semantic_score = float(score)

        entity_boost = calculate_entity_boost(
            query,
            chunk
        )

        final_score = (
            semantic_score
            + entity_boost
        )

        # Keep all scores for debugging
        chunk["semantic_score"] = (
            semantic_score
        )

        chunk["entity_boost"] = (
            entity_boost
        )

        chunk["score"] = (
            final_score
        )

        results.append(
            chunk
        )

    # --------------------------------------------------------
    # Sort by entity-aware final score
    # --------------------------------------------------------

    results = sorted(
        results,
        key=lambda x: x["score"],
        reverse=True
    )

    return results[:top_k]


# ============================================================
# BUILD EVIDENCE TEXT
# ============================================================

def evidence_text(results):

    parts = []

    for number, result in enumerate(
        results,
        start=1
    ):

        location = result["source"]

        if result.get("page") is not None:

            location += (
                f", page {result['page']}"
            )

        parts.append(
            f"""
[EVIDENCE {number}]
Source: {location}

{result['text']}
"""
        )

    return "\n".join(parts)


# ============================================================
# GENERATE FOLLOW-UP SEARCHES
# ============================================================

def generate_follow_up_queries(
    original_question,
    first_hop_results
):

    evidence = evidence_text(
        first_hop_results
    )

    prompt = f"""
You are planning the SECOND retrieval hop for a
multi-document question-answering system.

ORIGINAL QUESTION:

{original_question}


FIRST-HOP EVIDENCE:

{evidence}


Your job is NOT to answer the question.

Your job is to determine what relationship or fact is still
missing and generate search queries that can retrieve it.

Follow these rules carefully:

1. Identify concrete named entities discovered in the
   first-hop evidence.

2. Determine which discovered entity should become the
   subject of the second search.

3. Preserve exact entity names whenever possible.

4. Search for the missing relationship required by the
   original question.

5. Do not invent names or facts.

6. Do not simply repeat the original question unless useful.

7. Generate no more than {MAX_FOLLOW_UP_QUERIES} queries.

8. Pay close attention to the requested answer type in the
   original question.

9. If the question asks for an accord, your searches should
   specifically search for accords involving the discovered
   entity rather than generic conflicts.

10. Do not broaden a specific target type such as "accord"
    into generic terms such as "war", "battle", "event",
    or "conflict".

Example:

Original question:
"Which accord was ultimately won by the faction of which
Ederon Fellgard is a member?"

First hop discovers:
Ederon Fellgard -> member of The Iron-Ring Cartel

Good second-hop searches:

[
    "The Iron-Ring Cartel accord",
    "accord won by The Iron-Ring Cartel",
    "The Iron-Ring Cartel victor accord"
]

Return ONLY a valid JSON array of strings.
"""

    response = client.chat.completions.create(
        model="openai/gpt-4o-mini",

        messages=[
            {
                "role": "user",
                "content": prompt
            }
        ],

        temperature=0
    )

    raw = (
        response
        .choices[0]
        .message
        .content
        .strip()
    )

    raw = raw.replace(
        "```json",
        ""
    )

    raw = raw.replace(
        "```",
        ""
    )

    raw = raw.strip()

    try:

        queries = json.loads(
            raw
        )

        if not isinstance(
            queries,
            list
        ):
            return []

        return queries[
            :MAX_FOLLOW_UP_QUERIES
        ]

    except Exception:

        print()
        print(
            "Could not parse "
            "follow-up queries."
        )

        print(
            "LLM returned:"
        )

        print(raw)

        return []


# ============================================================
# DEDUPLICATE
# ============================================================

def deduplicate(results):

    seen = set()
    unique = []

    for result in results:

        chunk_id = result[
            "chunk_id"
        ]

        if chunk_id not in seen:

            seen.add(
                chunk_id
            )

            unique.append(
                result
            )

    return unique


# ============================================================
# SOURCE DIVERSITY
# ============================================================

def diversify_sources(
    results,
    max_per_source=2
):

    source_counts = {}
    diverse_results = []

    for result in results:

        source = result[
            "source"
        ]

        current_count = (
            source_counts.get(
                source,
                0
            )
        )

        if (
            current_count
            >= max_per_source
        ):
            continue

        diverse_results.append(
            result
        )

        source_counts[source] = (
            current_count + 1
        )

    return diverse_results


# ============================================================
# SCORE FILTER
# ============================================================

def filter_by_score(
    results,
    minimum_score
):

    # IMPORTANT:
    # Filter using semantic similarity,
    # NOT the boosted final score.

    return [
        result
        for result in results
        if result.get(
            "semantic_score",
            result["score"]
        ) >= minimum_score
    ]


# ============================================================
# FINAL ANSWER
# ============================================================

def generate_answer(
    question,
    evidence
):

    context = evidence_text(
        evidence
    )

    system_prompt = """
You are ByteKnights, an intelligent assistant for the
Ashen Era Archive.

Answer using ONLY the provided archive evidence.

Rules:

1. Do not use outside knowledge.
2. Never invent facts.
3. Trace multi-step relationships carefully.

4. Identify exactly what TYPE of thing the question asks
   for.

5. Only return entities that match that requested type.

6. For example:
   - "which accord" -> answer only an accord
   - "which person" -> answer only a person
   - "which faction" -> answer only a faction
   - "which location" -> answer only a location

7. Do not treat every conflict, battle, war, event, or
   victory as an accord unless the archive explicitly
   identifies it as an accord.

8. When a question requires multiple hops, briefly show
   the relationship chain.

9. Cite factual claims using [Evidence X].

10. If multiple evidence items support a claim, cite them.

11. If evidence conflicts, explain the conflict.

12. If more than one entity genuinely satisfies all
    conditions in the question, say that the evidence
    indicates multiple valid answers.

13. If the evidence is insufficient to identify an entity
    of the requested type, explicitly say so.

14. Pay close attention to exact entity names in the
    question. Do not answer about a similarly named entity.

15. If the question asks specifically about information
    visible in an image, portrait, map, figure, plate, or
    illustration, do not pretend textual evidence proves
    the visual detail. State when visual evidence would be
    required.
"""

    prompt = f"""
QUESTION:

{question}


ARCHIVE EVIDENCE:

{context}


Answer the question using only this evidence.
"""

    response = client.chat.completions.create(
        model="openai/gpt-4o-mini",

        messages=[
            {
                "role": "system",
                "content": system_prompt
            },
            {
                "role": "user",
                "content": prompt
            }
        ],

        temperature=0
    )

    return (
        response
        .choices[0]
        .message
        .content
    )


# ============================================================
# PROCESS ONE QUESTION
# ============================================================

def process_question(
    question
):

    # --------------------------------------------------------
    # HOP 1
    # --------------------------------------------------------

    print()
    print(
        "HOP 1: Searching original question..."
    )

    first_results = search(
        question,
        FIRST_HOP_K
    )

    # --------------------------------------------------------
    # SHOW RAW RESULTS
    # --------------------------------------------------------

    print()
    print(
        "Raw first-hop sources:"
    )

    for result in first_results:

        print(
            f"- {result['source']} "
            f"| final={result['score']:.4f} "
            f"| semantic="
            f"{result['semantic_score']:.4f} "
            f"| entity+="
            f"{result['entity_boost']:.4f}"
        )

    # --------------------------------------------------------
    # CLEAN HOP 1
    # --------------------------------------------------------

    first_results = filter_by_score(
        first_results,
        FIRST_HOP_THRESHOLD
    )

    first_results = deduplicate(
        first_results
    )

    first_results = diversify_sources(
        first_results,
        max_per_source=2
    )

    print()
    print(
        "Cleaned first-hop sources:"
    )

    for result in first_results:

        print(
            f"- {result['source']} "
            f"| final={result['score']:.4f} "
            f"| semantic="
            f"{result['semantic_score']:.4f} "
            f"| entity+="
            f"{result['entity_boost']:.4f}"
        )

    # --------------------------------------------------------
    # FOLLOW-UP QUERY GENERATION
    # --------------------------------------------------------

    print()
    print(
        "Analyzing first-hop evidence "
        "for missing connections..."
    )

    follow_up_queries = (
        generate_follow_up_queries(
            question,
            first_results
        )
    )

    print()
    print(
        "Generated follow-up searches:"
    )

    if not follow_up_queries:

        print(
            "- No follow-up searches generated."
        )

    for query in follow_up_queries:

        print(
            f"- {query}"
        )

    # --------------------------------------------------------
    # HOP 2
    # --------------------------------------------------------

    second_results = []

    for query in follow_up_queries:

        print()
        print(
            f"HOP 2 SEARCH: {query}"
        )

        results = search(
            query,
            SECOND_HOP_K
        )

        second_results.extend(
            results
        )

    # --------------------------------------------------------
    # CLEAN HOP 2
    # --------------------------------------------------------

    second_results = filter_by_score(
        second_results,
        SECOND_HOP_THRESHOLD
    )

    second_results = deduplicate(
        second_results
    )

    second_results = sorted(
        second_results,
        key=lambda x: x["score"],
        reverse=True
    )

    second_results = diversify_sources(
        second_results,
        max_per_source=2
    )

    # --------------------------------------------------------
    # COMBINE BOTH HOPS
    # --------------------------------------------------------

    combined = (
        first_results
        + second_results
    )

    combined = deduplicate(
        combined
    )

    combined = combined[
        :MAX_FINAL_EVIDENCE
    ]

    print()
    print(
        f"Combined evidence chunks: "
        f"{len(combined)}"
    )

    # --------------------------------------------------------
    # FINAL ANSWER
    # --------------------------------------------------------

    print()
    print(
        "Generating final answer..."
    )

    answer = generate_answer(
        question,
        combined
    )

    print()
    print(
        "================================"
    )

    print(
        "FINAL ANSWER"
    )

    print(
        "================================"
    )

    print()
    print(answer)

    # --------------------------------------------------------
    # SHOW EVIDENCE
    # --------------------------------------------------------

    print()
    print(
        "================================"
    )

    print(
        "EVIDENCE USED"
    )

    print(
        "================================"
    )

    for number, result in enumerate(
        combined,
        start=1
    ):

        print()

        print(
            f"[Evidence {number}] "
            f"{result['source']}"
        )

        if result.get(
            "page"
        ) is not None:

            print(
                f"Page: "
                f"{result['page']}"
            )

        print(
            f"Semantic similarity: "
            f"{result['semantic_score']:.4f}"
        )

        print(
            f"Entity boost: "
            f"{result['entity_boost']:.4f}"
        )

        print(
            f"Final score: "
            f"{result['score']:.4f}"
        )


# ============================================================
# MAIN LOOP
# ============================================================

def main():

    while True:

        print()
        print(
            "=" * 60
        )

        question = input(
            "Ask ByteKnights "
            "(or type 'exit'): "
        ).strip()

        if question.lower() in [
            "exit",
            "quit",
            "q"
        ]:

            print(
                "ByteKnights stopped."
            )

            break

        if not question:
            continue

        process_question(
            question
        )


# ============================================================
# START
# ============================================================

if __name__ == "__main__":
    main()