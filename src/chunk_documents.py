from pathlib import Path
import json


INPUT_FILE = Path("data/processed/documents_with_ocr.jsonl")
OUTPUT_FILE = Path("data/processed/chunks.jsonl")


CHUNK_SIZE = 500
CHUNK_OVERLAP = 100


def split_into_chunks(text, chunk_size=CHUNK_SIZE, overlap=CHUNK_OVERLAP):
    words = text.split()

    chunks = []

    if not words:
        return chunks

    start = 0

    while start < len(words):

        end = start + chunk_size

        chunk_words = words[start:end]

        chunk_text = " ".join(chunk_words)

        chunks.append(chunk_text)

        if end >= len(words):
            break

        start += chunk_size - overlap

    return chunks


def main():
    records = []

    with open(INPUT_FILE, "r", encoding="utf-8") as f:
        for line in f:
            records.append(json.loads(line))

    all_chunks = []

    chunk_id = 0

    for record in records:

        text = record["text"].strip()

        if not text:
            continue

        chunks = split_into_chunks(text)

        for local_index, chunk_text in enumerate(chunks):

            chunk = {
                "chunk_id": chunk_id,
                "source": record["source"],
                "path": record["path"],
                "type": record["type"],
                "page": record["page"],
                "chunk_index": local_index,
                "text": chunk_text
            }

            all_chunks.append(chunk)

            chunk_id += 1

    with open(
        OUTPUT_FILE,
        "w",
        encoding="utf-8"
    ) as f:

        for chunk in all_chunks:

            json.dump(
                chunk,
                f,
                ensure_ascii=False
            )

            f.write("\n")

    print()
    print("==============================")
    print("CHUNKING COMPLETE")
    print("==============================")

    print(f"Input records: {len(records)}")
    print(f"Chunks created: {len(all_chunks)}")

    if all_chunks:

        lengths = [
            len(chunk["text"].split())
            for chunk in all_chunks
        ]

        print(f"Smallest chunk: {min(lengths)} words")
        print(f"Largest chunk: {max(lengths)} words")
        print(
            f"Average chunk: "
            f"{sum(lengths) / len(lengths):.2f} words"
        )

    print()
    print(f"Saved to: {OUTPUT_FILE}")


if __name__ == "__main__":
    main()