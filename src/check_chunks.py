import json
from pathlib import Path


CHUNK_FILE = Path("data/processed/chunks.jsonl")


def main():

    chunks = []

    with open(CHUNK_FILE, "r", encoding="utf-8") as f:

        for line in f:
            chunks.append(json.loads(line))

    print(f"Total chunks: {len(chunks)}")

    print()
    print("===== SAMPLE CHUNKS =====")

    for chunk in chunks[:5]:

        print()
        print("--------------------------------")
        print(f"Chunk ID: {chunk['chunk_id']}")
        print(f"Source: {chunk['source']}")
        print(f"Page: {chunk['page']}")
        print(f"Chunk index: {chunk['chunk_index']}")
        print("--------------------------------")

        print(chunk["text"][:1500])


if __name__ == "__main__":
    main()