# 🧾 Bewirtungsbeleg Agent

**From receipt to tax-compliant PDF — fully automated.**

You send a receipt and a few lines of context. The agent takes care of everything else.

---

## What it does

German tax law requires a *Bewirtungsbeleg* for every business meal — a document that captures the occasion, participants, amount, and your signature. In practice, this is painful:

- receipts are blurry, incomplete, or in a foreign language
- tips paid by card don't appear on the receipt, causing mismatches with bank transactions
- mandatory fields (occasion, participants) are never on the receipt itself
- files get named inconsistently and signatures are missing

This agent solves all of that. You send an email with the receipt attached and a short description. You get back a finished, signed, accounting-ready PDF.

---

## How it works

```
Receipt (PDF/JPG/PNG) + short email text
        ↓
    OCR (Gemini)
        ↓
  LLM extraction → structured JSON
        ↓
   Tip reconciliation logic
        ↓
  Fill Word template → convert to PDF
        ↓
  Merge receipt + form → final PDF
        ↓
  Clean filename + send back
```

**Key features:**
- OCR handles PDFs, JPGs, and PNGs including low-quality phone photos
- LLM extracts all required fields: date, restaurant, address, occasion, participants, amount
- Smart tip logic: if you paid a tip by card, just mention it in the email — the agent reconciles the amount so it matches your bank transaction
- Signature injected automatically from a stored image
- Output is named consistently: `Bewirtungsbeleg_2025-07-09_Restaurant-Name_36,80-EUR.pdf`
- Ready for DATEV, lexoffice, or direct forwarding to accounting

---

## Tech stack

| Layer | Technology |
|---|---|
| API | FastAPI + uvicorn |
| OCR | Gemini 2.5 Flash (multimodal) |
| LLM extraction | Gemini 2.5 Flash |
| PDF generation | python-docx → LibreOffice headless |
| PDF merging | PyPDF2 |
| Multi-tenancy | PostgreSQL via psycopg3 |
| Workflow / email | n8n |
| Deployment | Docker + Railway |

---

## API endpoints

### `POST /full-agent`
End-to-end: takes a receipt file + email text, returns a finished PDF.

| Field | Type | Description |
|---|---|---|
| `receipt` | file | Receipt as PDF, JPG, or PNG |
| `email_text` | string | Occasion, participants, optional tip |
| `tenant_key` | string | Tenant identifier (default: `"default"`) |

### `POST /build-bewirtungsbeleg`
Takes pre-structured JSON data + receipt, fills the template and returns PDF. Useful if you're bringing your own extraction logic.

---

## Setup

### Requirements
- Python 3.12+
- Docker (for deployment)
- LibreOffice (included in Docker image)
- PostgreSQL database for tenant storage
- Gemini API key

### Environment variables

```
GEMINI_API_KEY=your_key_here
TENANT_DATABASE_URL=postgresql://user:password@host:port/dbname
PORT=8000
```

### Run locally

```bash
pip install -r requirements.txt
uvicorn service:app --reload
```

### Run with Docker

```bash
docker build -t bewirtungsbeleg-agent .
docker run -p 8000:8000 \
  -e GEMINI_API_KEY=... \
  -e TENANT_DATABASE_URL=... \
  bewirtungsbeleg-agent
```

---

## Multi-tenancy

Each tenant has their own signature, default city, reply-from email, and template. The `tenant_store.py` module looks up tenants from a PostgreSQL table:

```sql
CREATE TABLE tenants (
    tenant_key         TEXT PRIMARY KEY,
    display_name       TEXT,
    default_city       TEXT,
    signature_png_b64  TEXT,
    reply_from_email   TEXT,
    template_key       TEXT
);
```

If a tenant key is not found, the agent falls back to `"default"`.

---

## Tip handling

Tips paid by card are a common source of accounting errors — the receipt shows one amount, the bank transaction shows another. The agent handles this with a priority-based reconciliation:

1. If the email contains an explicit total (e.g. *"insgesamt 36,80 EUR"*) → use that
2. If the email mentions a tip (e.g. *"Trinkgeld 5 EUR"*) → add to receipt amount
3. If the OCR text contains a total (Gesamtbetrag, Zu zahlen) → use that
4. If the OCR text contains a tip line → add to base amount
5. Fallback to LLM-extracted amount

---

## Status

- ✅ Fully working end-to-end pipeline
- ✅ Deployed on Railway
- ✅ Used in production internally at [ephema.io](https://www.ephema.io)
- 🔜 External testing opening shortly

---

## Contact

Built by **Johannes Köhler** — Founders Associate at ephema, Berlin/Paris.

- Email: johannes@ephema.io
- LinkedIn: [linkedin.com/in/johannes-köhler-9245b21b9](https://www.linkedin.com/in/johannes-köhler-9245b21b9)
- Demo: [ephema.notion.site/Bewirtungsbeleg-Agent](https://ephema.notion.site/Bewirtungsbeleg-Agent-2e476cd111b5808ca772f160dd2a6cde)
