from pathlib import Path
import os
import pickle

import faiss
import numpy as np

from dotenv import load_dotenv
from openai import OpenAI
from sentence_transformers import SentenceTransformer


# ==========================================
# Configuration
# ==========================================

INDEX_FILE = Path("data/index/archive.index")
METADATA_FILE = Path("data/index/chunks.pkl")

EMBEDDING_MODEL = "all-MiniLM-L6-v2"

TOP_K = 6


# ==========================================
# Load environment variables
# ==========================================

load_dotenv()

api_key = os.getenv("OPENROUTER_API_KEY")

if not api_key:
    raise ValueError(
        "OPENROUTER_API_KEY was not found. "
        "Check your .env file."
    )


# ==========================================
# LLM client
# ==========================================

client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=api_key
)


# ==========================================
# Load retrieval system
# ==========================================

print("Loading ArchiveMind...")

embedding_model = SentenceTransformer(
    EMBEDDING_MODEL
)

index = faiss.read_index(
    str(INDEX_FILE)
)

with open(METADATA_FILE, "rb") as f:
    chunks = pickle.load(f)

print(f"Loaded {len(chunks)} archive chunks.")
print("ArchiveMind is ready.")
print()


# ==========================================
# Retrieval
# ==========================================

def retrieve(question):

    query_embedding = embedding_model.encode(
        [question],
        normalize_embeddings=True
    )

    query_embedding = np.array(
        query_embedding,
        dtype="float32"
    )

    scores, indices = index.search(
        query_embedding,
        TOP_K
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


# ==========================================
# Build context for LLM
# ==========================================

def build_context(results):

    context_parts = []

    for number, result in enumerate(
        results,
        start=1
    ):

        page = result["page"]

        if page is None:
            location = result["source"]
        else:
            location = (
                f"{result['source']}, "
                f"page {page}"
            )

        context = f"""
[SOURCE {number}]
Location: {location}
Chunk ID: {result['chunk_id']}

{result['text']}
"""

        context_parts.append(context)

    return "\n".join(context_parts)


# ==========================================
# Generate grounded answer
# ==========================================

def generate_answer(question, results):

    context = build_context(results)

    system_prompt = """
You are ArchiveMind, an intelligent assistant for the
Ashen Era Archive.

You must answer questions using ONLY the archive evidence
provided to you.

Rules:

1. Do not use outside knowledge.
2. Do not invent facts.
3. If the supplied evidence is insufficient, clearly say so.
4. When making a factual claim, cite the supporting source
   using [Source X].
5. Multiple sources may be cited when appropriate.
6. If sources disagree, explicitly describe the disagreement.
7. Prefer a concise direct answer followed by supporting
   explanation.
8. Never pretend that text evidence describes visual details
   that are only contained in an image.
"""

    user_prompt = f"""
QUESTION:

{question}


ARCHIVE EVIDENCE:

{context}


Answer the question using only the archive evidence above.
"""

    response = client.chat.completions.create(

        # We can change this model later.
        model="openai/gpt-4o-mini",

        messages=[
            {
                "role": "system",
                "content": system_prompt
            },
            {
                "role": "user",
                "content": user_prompt
            }
        ],

        temperature=0
    )

    return response.choices[0].message.content


# ==========================================
# Display sources
# ==========================================

def print_sources(results):

    print()
    print("================================")
    print("RETRIEVED SOURCES")
    print("================================")

    for number, result in enumerate(
        results,
        start=1
    ):

        print()

        print(
            f"[Source {number}] "
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


# ==========================================
# Main
# ==========================================

def main():

    question = input(
        "Ask ByteKnights: "
    ).strip()

    if not question:
        print("Please enter a question.")
        return

    print()
    print("Searching the archive...")

    results = retrieve(question)

    print("Generating grounded answer...")
    print()

    answer = generate_answer(
        question,
        results
    )

    print("================================")
    print("ANSWER")
    print("================================")
    print()
    print(answer)

    print_sources(results)


if __name__ == "__main__":
    main()