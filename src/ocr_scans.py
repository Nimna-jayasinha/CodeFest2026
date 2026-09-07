from pathlib import Path
import json
import fitz
import pytesseract
from PIL import Image
import io

DATA_FILE = Path("data/processed/documents.jsonl")
OUTPUT_FILE = Path("data/processed/documents_with_ocr.jsonl")

# Change this if your Tesseract is installed somewhere else
pytesseract.pytesseract.tesseract_cmd = (
    r"C:\Program Files\Tesseract-OCR\tesseract.exe"
)


def ocr_pdf_page(pdf_path, page_number):
    doc = fitz.open(pdf_path)

    page = doc[page_number - 1]

    pix = page.get_pixmap(matrix=fitz.Matrix(2, 2))

    image_bytes = pix.tobytes("png")

    image = Image.open(io.BytesIO(image_bytes))

    text = pytesseract.image_to_string(image)

    doc.close()

    return text


def main():
    records = []

    with open(DATA_FILE, "r", encoding="utf-8") as f:
        for line in f:
            records.append(json.loads(line))

    fixed = 0

    for record in records:

        if record["text"].strip():
            continue

        if record["type"] != ".pdf":
            continue

        source_path = Path(record["path"])

        print(
            f"OCR: {record['source']} "
            f"page {record['page']}"
        )

        try:
            text = ocr_pdf_page(
                source_path,
                record["page"]
            )

            record["text"] = text

            if text.strip():
                fixed += 1

        except Exception as e:
            print(f"ERROR: {e}")

    with open(
        OUTPUT_FILE,
        "w",
        encoding="utf-8"
    ) as f:

        for record in records:
            json.dump(
                record,
                f,
                ensure_ascii=False
            )
            f.write("\n")

    remaining_empty = sum(
        1
        for record in records
        if not record["text"].strip()
    )

    print()
    print("==============================")
    print("OCR COMPLETE")
    print("==============================")
    print(f"Records recovered: {fixed}")
    print(f"Still empty: {remaining_empty}")
    print(f"Saved to: {OUTPUT_FILE}")


if __name__ == "__main__":
    main()