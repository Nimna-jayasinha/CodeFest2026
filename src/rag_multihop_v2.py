from pathlib import Path
import os
import pickle
import json

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
# LOAD SEARCH SYSTEM
# ============================================================

print("Loading ByteKnights Multi-Hop RAG...")

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
# VECTOR SEARCH
# ============================================================

def search(query, top_k):

    embedding = embedding_model.encode(
        [query],
        normalize_embeddings=True
    )

    embedding = np.array(
        embedding,
        dtype="float32"
    )

    scores, indices = index.search(
        embedding,
        top_k
    )

    results = []

    for score, index_id in zip(
        scores[0],
        indices[0]
    ):

        chunk = chunks[index_id].copy()

        chunk["score"] = float(score)

        results.append(chunk)

    return results


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

        if result["page"] is not None:
            location += f", page {result['page']}"

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
You are helping search a fictional document archive.

We need to answer this question:

{original_question}

We already performed one search and retrieved this evidence:

{evidence}

The question may require connecting facts across documents.

Determine what facts/entities were discovered in the first
search and what should be searched for next.

Generate at most {MAX_FOLLOW_UP_QUERIES} short search queries.

Important:
- Use names and entities actually found in the evidence.
- Do not answer the original question.
- Do not invent entities.
- Search for the missing relationship needed to answer.
- Return ONLY a JSON array of strings.

Example:

[
  "Iron-Ring Cartel accords",
  "Iron-Ring Cartel victory",
  "accord won by Iron-Ring Cartel"
]
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

    raw = response.choices[0].message.content.strip()

    # Remove markdown fences if the model uses them
    raw = raw.replace("```json", "")
    raw = raw.replace("```", "")
    raw = raw.strip()

    try:

        queries = json.loads(raw)

        if not isinstance(queries, list):
            return []

        return queries[:MAX_FOLLOW_UP_QUERIES]

    except Exception:

        print()
        print("Could not parse follow-up queries.")
        print("LLM returned:")
        print(raw)

        return []


# ============================================================
# DEDUPLICATE RESULTS
# ============================================================

def deduplicate(results):

    seen = set()
    unique = []

    for result in results:

        chunk_id = result["chunk_id"]

        if chunk_id not in seen:

            seen.add(chunk_id)

            unique.append(result)

    return unique

def diversify_sources(results, max_per_source=2):

    source_counts = {}
    diverse_results = []

    for result in results:

        source = result["source"]

        current_count = source_counts.get(
            source,
            0
        )

        if current_count >= max_per_source:
            continue

        diverse_results.append(result)

        source_counts[source] = (
            current_count + 1
        )

    return diverse_results


def filter_by_score(
    results,
    minimum_score
):

    return [
        result
        for result in results
        if result["score"] >= minimum_score
    ]
# ============================================================
# FINAL ANSWER
# ============================================================

def generate_answer(question, evidence):

    context = evidence_text(evidence)

    system_prompt = """
You are ByteKnights, an intelligent assistant for the
Ashen Era Archive.

Answer using ONLY the provided archive evidence.

Rules:

1. Do not use outside knowledge.
2. Never invent facts.
3. Trace multi-step relationships carefully.
4. When a question requires multiple hops, explain the
   reasoning chain briefly.
5. Cite factual claims using [Evidence X].
6. If multiple evidence items support a claim, cite them.
7. If evidence conflicts, explain the conflict.
8. If evidence is still insufficient, explicitly say so.
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

    return response.choices[0].message.content


# ============================================================
# MAIN
# ============================================================

def main():

    question = input(
        "Ask ByteKnights: "
    ).strip()

    if not question:
        return

    # --------------------------------------------------------
    # HOP 1
    # --------------------------------------------------------

    print()
    print("HOP 1: Searching original question...")

    first_results = search(
        question,
        FIRST_HOP_K
    )

    print()
    print("First-hop sources:")

    for result in first_results:

        print(
            f"- {result['source']} "
            f"({result['score']:.4f})"
        )

    # --------------------------------------------------------
    # GENERATE FOLLOW-UP QUERIES
    # --------------------------------------------------------

    print()
    print(
        "Analyzing first-hop evidence "
        "for missing connections..."
    )

    follow_up_queries = generate_follow_up_queries(
        question,
        first_results
    )

    print()
    print("Generated follow-up searches:")

    for query in follow_up_queries:
        print(f"- {query}")

    # --------------------------------------------------------
    # HOP 2
    # --------------------------------------------------------

    second_results = []

    for query in follow_up_queries:

        print()
        print(f"HOP 2 SEARCH: {query}")

        results = search(
            query,
            SECOND_HOP_K
        )

        second_results.extend(
            results
        )

    # --------------------------------------------------------
    # COMBINE
    # --------------------------------------------------------

    combined = (
        first_results +
        second_results
    )

    combined = deduplicate(
        combined
    )

    print()
    print(
        f"Combined evidence chunks: "
        f"{len(combined)}"
    )

    # --------------------------------------------------------
    # ANSWER
    # --------------------------------------------------------

    print()
    print("Generating final answer...")

    answer = generate_answer(
        question,
        combined
    )

    print()
    print("================================")
    print("FINAL ANSWER")
    print("================================")
    print()
    print(answer)

    # --------------------------------------------------------
    # SHOW SOURCES
    # --------------------------------------------------------

    print()
    print("================================")
    print("EVIDENCE USED")
    print("================================")

    for number, result in enumerate(
        combined,
        start=1
    ):

        print()

        print(
            f"[Evidence {number}] "
            f"{result['source']}"
        )

        if result["page"] is not None:

            print(
                f"Page: {result['page']}"
            )

        print(
            f"Similarity: "
            f"{result['score']:.4f}"
        )


if __name__ == "__main__":
    main()