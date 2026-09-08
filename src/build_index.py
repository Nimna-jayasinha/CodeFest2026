from pathlib import Path
import json
import pickle

import faiss
import numpy as np
from sentence_transformers import SentenceTransformer


CHUNKS_FILE = Path("data/processed/chunks.jsonl")

INDEX_DIR = Path("data/index")

FAISS_FILE = INDEX_DIR / "archive.index"
METADATA_FILE = INDEX_DIR / "chunks.pkl"


MODEL_NAME = "all-MiniLM-L6-v2"


def load_chunks():
    chunks = []

    with open(CHUNKS_FILE, "r", encoding="utf-8") as f:
        for line in f:
            chunks.append(json.loads(line))

    return chunks


def main():

    print("Loading chunks...")

    chunks = load_chunks()

    print(f"Chunks loaded: {len(chunks)}")

    texts = [
        chunk["text"]
        for chunk in chunks
    ]

    print()
    print("Loading embedding model...")

    model = SentenceTransformer(MODEL_NAME)

    print()
    print("Creating embeddings...")

    embeddings = model.encode(
        texts,
        batch_size=32,
        show_progress_bar=True,
        normalize_embeddings=True
    )

    embeddings = np.array(
        embeddings,
        dtype="float32"
    )

    print()
    print(f"Embedding shape: {embeddings.shape}")

    print()
    print("Building FAISS index...")

    dimension = embeddings.shape[1]

    index = faiss.IndexFlatIP(dimension)

    index.add(embeddings)

    INDEX_DIR.mkdir(
        parents=True,
        exist_ok=True
    )

    faiss.write_index(
        index,
        str(FAISS_FILE)
    )

    with open(
        METADATA_FILE,
        "wb"
    ) as f:
        pickle.dump(
            chunks,
            f
        )

    print()
    print("==============================")
    print("INDEX BUILD COMPLETE")
    print("==============================")
    print(f"Vectors stored: {index.ntotal}")
    print(f"Vector dimension: {dimension}")
    print(f"FAISS index: {FAISS_FILE}")
    print(f"Metadata: {METADATA_FILE}")


if __name__ == "__main__":
    main()