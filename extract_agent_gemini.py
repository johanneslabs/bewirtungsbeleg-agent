import os
import json

import google.generativeai as genai
import requests

# ---------- Konfiguration ----------

# Gemini API Key aus ENV
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
if not GEMINI_API_KEY:
    raise RuntimeError("Bitte setze zuerst GEMINI_API_KEY in der Umgebung.")

genai.configure(api_key=GEMINI_API_KEY)

MODEL_NAME = "gemini-2.5-flash"

# URL deiner lokalen FastAPI-Instanz
API_URL = "http://127.0.0.1:8000/build-bewirtungsbeleg"

# Pfad zu einem Beispiel-Bon (für den API-Call am Ende)
RECEIPT_PATH = "input/bon_beispiel.pdf"


# ---------- Prompt für Extraktion ----------

EXTRACTION_SYSTEM_PROMPT = """
Du extrahierst aus Restaurantbelegen und Beschreibungen strukturierte Bewirtungsdaten.
Du antwortest *ausschließlich* mit einem JSON-Objekt im folgenden Schema:

{
  "bewirtungsdatum": "TT.MM.JJJJ",
  "unterschriftsdatum": "TT.MM.JJJJ",
  "ort": "Ort der Unterschrift, z.B. Berlin",
  "restaurant": "Name des Restaurants",
  "adresse": "Adresse des Restaurants, falls erkennbar",
  "anlass": "1-Satz-Beschreibung des Anlasses",
  "personen": ["Person 1", "Person 2", ...],
  "betrag": "Gesamtbetrag inklusive Währung, z.B. '30,60 EUR'"
}

Regeln:
- Verwende für 'bewirtungsdatum' das Datum auf dem Beleg.
- 'unterschriftsdatum' = heutiges Datum (wenn kein anderes genannt wird).
- 'ort' = Ort aus dem Anlass-Text oder sonst Unternehmenssitz ('Berlin').
- 'personen' aus dem E-Mail-/Beschreibungstext extrahieren, nicht aus dem Bon.
- 'betrag' immer vom Beleg übernehmen.
- Wenn Informationen fehlen: leere Strings oder best guess, aber *niemals erfinden*.
- Keine zusätzlichen Erklärungen. Nur das JSON zurückgeben.
"""


def build_user_prompt(receipt_text: str, email_text: str | None = None) -> str:
    parts = []
    parts.append("OCR-Text des Bons:\n" + receipt_text.strip())
    if email_text:
        parts.append("\nZusätzliche Beschreibung / E-Mail-Text:\n" + email_text.strip())
    return "\n\n".join(parts)


# ---------- Hauptfunktion: Extraktion mit Gemini ----------

def extract_bewirtungsdaten_gemini(receipt_text: str, email_text: str | None = None) -> dict:
    """
    Nutzt Gemini, um strukturierte Bewirtungsdaten aus Text zu extrahieren.
    """
    user_prompt = build_user_prompt(receipt_text, email_text)

    model = genai.GenerativeModel(MODEL_NAME)
    response = model.generate_content(
        [
            EXTRACTION_SYSTEM_PROMPT,
            user_prompt,
        ]
    )

    raw = response.text.strip()

    # Falls Gemini ```json ... ``` verwendet, säubern wir das weg
    if "```" in raw:
        start = raw.find("{")
        end = raw.rfind("}")
        raw = raw[start:end+1]

    data = json.loads(raw)
    return data


# ---------- Aufruf deiner lokalen PDF-API ----------

def call_bewirtungs_api(bewirtungs_data: dict, receipt_path: str) -> str:
    """
    Ruft deine FastAPI (/build-bewirtungsbeleg) auf und gibt den Pfad zur fertigen PDF zurück.
    """
    data_str = json.dumps(bewirtungs_data, ensure_ascii=False)

    with open(receipt_path, "rb") as f:
        files = {
            "receipt": (os.path.basename(receipt_path), f, "application/pdf"),
        }
        form_data = {
            "data": data_str,
        }
        resp = requests.post(API_URL, data=form_data, files=files)

    if resp.status_code != 200:
        raise RuntimeError(f"API-Fehler: {resp.status_code} - {resp.text}")

    out_path = "output/bewirtungsbeleg_von_gemini_agent.pdf"
    with open(out_path, "wb") as f:
        f.write(resp.content)

    return out_path


# ---------- Demo-Run ----------

if __name__ == "__main__":
    # 1) Dummy-Text, so tun als wäre er von OCR
    dummy_receipt_text = """
SaPHI Sushi & Bowl
Reichenberger Str. 120
10999 Berlin

Datum: 09.07.2025
Tisch: 4
Summe: 30,60 EUR (inkl. MwSt)

Vielen Dank für Ihren Besuch!
"""

    # 2) Dummy-E-Mail-/Beschreibungstext
    dummy_email_text = """
Lunch mit Christian Haug und Pascal Stichler von ZuBerlin.
Nachbesprechung zu den Ergebnissen vom ZuBerlin-Event, Lessons Learned und Aufgabenverteilung.
"""

    print("Rufe Gemini zur Extraktion auf...")
    bew_data = extract_bewirtungsdaten_gemini(dummy_receipt_text, dummy_email_text)

    print("\nExtrahierte Daten:")
    print(json.dumps(bew_data, indent=2, ensure_ascii=False))

    # 3) Optional: direkt deine PDF-API anrufen
    if os.path.exists(RECEIPT_PATH):
        print("\nRufe deine FastAPI-Bewirtungs-API auf...")
        pdf_path = call_bewirtungs_api(bew_data, RECEIPT_PATH)
        print(f"Fertige PDF vom Gemini-Agent gespeichert unter: {pdf_path}")
    else:
        print(f"\nHinweis: {RECEIPT_PATH} nicht gefunden, API-Call wurde übersprungen.")
