import os
import re
import base64
from pathlib import Path

from dotenv import load_dotenv
from openai import OpenAI


load_dotenv()

ARCHIVE_DIR = Path(r"H:\Codefest2026\Ashen_Era_Archive")

client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=os.getenv("OPENROUTER_API_KEY")
)

VISION_MODEL = "google/gemini-2.5-flash"


VISUAL_KEYWORDS = [
    "image",
    "figure",
    "figure plate",
    "plate",
    "portrait",
    "illustration",
    "illustrating",
    "pictured",
    "shown",
    "depicted",
    "banner",
    "emblem",
    "holding",
    "map",
]


def is_visual_question(question):
    q = question.lower()

    return any(keyword in q for keyword in VISUAL_KEYWORDS)


def normalize_name(text):
    text = text.lower()
    text = re.sub(r"[^a-z0-9]+", "_", text)
    return text.strip("_")


def find_matching_images(question):
    """
    Search archive PNG filenames for entity words found in the question.
    """

    question_words = set(
        normalize_name(question).split("_")
    )

    images = list(ARCHIVE_DIR.rglob("*.png"))

    scored = []

    for image in images:
        stem = normalize_name(image.stem)

        words = [
            word
            for word in stem.split("_")
            if len(word) >= 4
        ]

        score = 0

        for word in words:
            if word in question_words:
                score += 1

        if score > 0:
            scored.append((score, image))

    scored.sort(
        key=lambda x: x[0],
        reverse=True
    )

    # Remove duplicate filenames / duplicate copies
    unique = []
    seen_names = set()

    for score, path in scored:

        if path.name in seen_names:
            continue

        seen_names.add(path.name)
        unique.append((score, path))

    return unique[:5]


def encode_image(image_path):

    suffix = image_path.suffix.lower()

    mime_type = {
        ".png": "image/png",
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".webp": "image/webp",
    }.get(suffix, "image/png")

    with open(image_path, "rb") as image_file:
        encoded = base64.b64encode(
            image_file.read()
        ).decode("utf-8")

    return f"data:{mime_type};base64,{encoded}"


def answer_visual_question(question):

    matches = find_matching_images(question)

    if not matches:
        return {
            "answer": "No relevant archive image could be found.",
            "image": None
        }

    print("\nVISUAL: Candidate archive images:")

    for score, path in matches:
        print(
            f"- {path.name} | match_score={score}"
        )

    image_path = matches[0][1]

    print(
        f"\nVISUAL: Using image: {image_path}"
    )

    image_data = encode_image(image_path)

    response = client.chat.completions.create(
        model=VISION_MODEL,
        temperature=0,
        max_tokens=300,
        messages=[
            {
                "role": "system",
                "content": (
                    "You are examining an image from the Ashen Era Archive. "
                    "Answer only from what is visibly present in the supplied image. "
                    "Do not use outside knowledge. "
                    "Do not infer facts merely from the filename. "
                    "If the requested detail cannot actually be seen or read in the image, "
                    "say that the visual evidence is insufficient."
                )
            },
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": (
                            f"Question: {question}\n\n"
                            "Inspect this archive image carefully. "
                            "Return a short factual answer based only on the visual evidence."
                        )
                    },
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": image_data
                        }
                    }
                ]
            }
        ]
    )

    answer = response.choices[0].message.content

    return {
        "answer": answer,
        "image": str(image_path)
    }


if __name__ == "__main__":

    while True:

        question = input(
            "\nAsk visual RAG (or type 'exit'): "
        ).strip()

        if question.lower() == "exit":
            break

        if not question:
            continue

        if not is_visual_question(question):

            print(
                "\nThis does not appear to be a visual question."
            )
            continue

        result = answer_visual_question(question)

        print("\n================================")
        print("VISUAL ANSWER")
        print("================================")

        print(result["answer"])

        if result["image"]:
            print(
                f"\nImage evidence: {result['image']}"
            )