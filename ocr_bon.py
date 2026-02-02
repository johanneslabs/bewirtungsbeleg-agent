import os
from typing import Literal

import google.generativeai as genai
from PIL import Image

# Gemini API Key aus ENV
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
if not GEMINI_API_KEY:
    raise RuntimeError("Missing GEMINI_API_KEY or GOOGLE_API_KEY environment variable")

genai.configure(api_key=GEMINI_API_KEY)

MODEL_NAME = "gemini-2.5-flash"


def ocr_bon(path: str) -> str:
    """
    Macht OCR auf einem Bon – egal ob JPG/PNG oder PDF.
    Gibt reinen Text zurück (kein JSON, keine Interpretation).
    """
    model = genai.GenerativeModel(MODEL_NAME)

    prompt = """
    Lies den Text dieses Restaurantbelegs so gut wie möglich aus.
    Gib NUR den erkannten Text zurück, ohne zusätzliche Kommentare,
    Erklärungen oder JSON. Zeilenumbrüche bitte beibehalten.
    """

    ext = os.path.splitext(path)[1].lower()

    if ext in [".jpg", ".jpeg", ".png"]:
        # Bild direkt laden
        img = Image.open(path).convert("RGB")
        response = model.generate_content([prompt, img])

    elif ext == ".pdf":
        # PDF als Datei an Gemini schicken
        file = genai.upload_file(path=path)
        response = model.generate_content([prompt, file])

    else:
        raise ValueError(f"Ungültiger Dateityp für OCR: {ext}")

    return response.text


if __name__ == "__main__":
    example_path = "input/bon_beispiel.jpg"  # oder .pdf, wie du willst
    if not os.path.exists(example_path):
        print(f"Beispiel fehlt: {example_path}")
    else:
        text = ocr_bon(example_path)
        print("OCR-Ergebnis:\n")
        print(text)
