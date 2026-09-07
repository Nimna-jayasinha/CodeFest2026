import json
from pathlib import Path

DATA_FILE = Path("data/processed/documents.jsonl")


def main():
    records = []

    with open(DATA_FILE, "r", encoding="utf-8") as f:
        for line in f:
            records.append(json.loads(line))

    print(f"Total records: {len(records)}")
    print()

    # Show first 5 non-empty records
    print("===== SAMPLE NON-EMPTY RECORDS =====")

    shown = 0

    for record in records:
        text = record["text"].strip()

        if text:
            print()
            print("--------------------------------")
            print(f"Source: {record['source']}")
            print(f"Type: {record['type']}")
            print(f"Page: {record['page']}")
            print("--------------------------------")
            print(text[:1000])

            shown += 1

            if shown == 5:
                break

    # Show empty records
    print()
    print()
    print("===== EMPTY RECORDS =====")

    empty_records = [
        record
        for record in records
        if not record["text"].strip()
    ]

    print(f"Empty records: {len(empty_records)}")

    for record in empty_records:
        print(
            f"{record['source']} | "
            f"type={record['type']} | "
            f"page={record['page']}"
        )


if __name__ == "__main__":
    main()