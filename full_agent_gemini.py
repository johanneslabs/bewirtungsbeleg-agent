import os
import json
from PIL import Image

from ocr_bon import ocr_bon
from extract_agent_gemini import (
    extract_bewirtungsdaten_gemini,
    call_bewirtungs_api,
)

# WÄHLE DEINE INPUT-DATEI:
# jpg / jpeg / png / pdf — alles funktioniert
BON_INPUT = "input/bon_beispiel.jpg"


def image_to_pdf(image_path: str, pdf_path: str):
    """
    Konvertiert JPG/PNG zu einem einseitigen PDF für die FastAPI.
    """
    img = Image.open(image_path).convert("RGB")
    img.save(pdf_path, "PDF")


if __name__ == "__main__":
    if not os.path.exists(BON_INPUT):
        raise FileNotFoundError(f"Bon-Datei nicht gefunden: {BON_INPUT}")

    # 1) OCR (egal ob Bild oder PDF)
    print("📸 Starte OCR auf dem Bon...")
    ocr_text = ocr_bon(BON_INPUT)

    print("\n🔎 OCR-Text:")
    print("----------------------------------------")
    print(ocr_text)
    print("----------------------------------------")

    # 2) AI-Extraktion (Gemini 2.5 Flash)
    dummy_email_text = """
Lunch mit Geschäftspartnern.
Anlass: Besprechung zu laufenden Projekten und nächsten Schritten.
"""

    print("\n🤖 Extrahiere strukturierte Bewirtungsdaten...")
    bew_data = extract_bewirtungsdaten_gemini(ocr_text, dummy_email_text)

    print("\n🧾 Extrahierte Daten:")
    print(json.dumps(bew_data, indent=2, ensure_ascii=False))

    # 3) Sicherstellen, dass wir eine PDF für deine FastAPI haben
    ext = os.path.splitext(BON_INPUT)[1].lower()
    if ext == ".pdf":
        bon_pdf_path = BON_INPUT
    elif ext in [".jpg", ".jpeg", ".png"]:
        bon_pdf_path = "input/bon_input_converted.pdf"
        print("\n🖨 Wandle Bon-Bild in PDF um...")
        image_to_pdf(BON_INPUT, bon_pdf_path)
    else:
        raise ValueError(f"Ungültiger Dateityp für FastAPI: {ext}")

    # 4) PDF erzeugen durch deine FastAPI
    print("\n📄 Rufe deine FastAPI-Bewirtungs-API auf...")
    final_pdf_path = call_bewirtungs_api(bew_data, bon_pdf_path)

    print(f"\n✅ FERTIG! Bewirtungsbeleg liegt unter: {final_pdf_path}")
