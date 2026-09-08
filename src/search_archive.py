from pathlib import Path
import pickle

import faiss
import numpy as np
from sentence_transformers import SentenceTransformer


INDEX_FILE = Path("data/index/archive.index")
METADATA_FILE = Path("data/index/chunks.pkl")

MODEL_NAME = "all-MiniLM-L6-v2"


def main():

    print("Loading search system...")

    model = SentenceTransformer(MODEL_NAME)

    index = faiss.read_index(
        str(INDEX_FILE)
    )

    with open(
        METADATA_FILE,
        "rb"
    ) as f:
        chunks = pickle.load(f)

    print("Ready.")
    print()

    question = input(
        "Ask a question about the Ashen Era Archive: "
    )

    query_embedding = model.encode(
        [question],
        normalize_embeddings=True
    )

    query_embedding = np.array(
        query_embedding,
        dtype="float32"
    )

    TOP_K = 5

    scores, indices = index.search(
        query_embedding,
        TOP_K
    )

    print()
    print("================================")
    print("TOP SEARCH RESULTS")
    print("================================")

    for rank, (score, index_id) in enumerate(
        zip(scores[0], indices[0]),
        start=1
    ):

        chunk = chunks[index_id]

        print()
        print(f"RESULT #{rank}")
        print(f"Score: {score:.4f}")
        print(f"Source: {chunk['source']}")
        print(f"Page: {chunk['page']}")
        print(f"Chunk: {chunk['chunk_index']}")
        print("--------------------------------")

        print(chunk["text"][:1500])

        print()
        print("================================")


if __name__ == "__main__":
    main()