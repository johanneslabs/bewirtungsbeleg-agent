# full_agent_gemini.py
import os
import re
import base64
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Tuple

from fastapi import UploadFile

from tenant_store import get_tenant
from ocr_bon import ocr_bon
from extract_agent_gemini import extract_bewirtungsdaten_gemini


# -----------------------------
# Signature helper
# -----------------------------
def write_signature_tmp(signature_b64: str, tenant_key: str) -> str:
    """
    Writes base64 PNG to /tmp/signatures/<tenant>.png and returns that path.
    Accepts raw base64 OR data-url like 'data:image/png;base64,...'
    """
    signature_b64 = (signature_b64 or "").strip()
    if not signature_b64:
        raise ValueError("Empty signature_b64")

    # allow data-url
    if "base64," in signature_b64:
        signature_b64 = signature_b64.split("base64,", 1)[1].strip()

    sig_dir = Path("/tmp/signatures")
    sig_dir.mkdir(parents=True, exist_ok=True)

    sig_path = sig_dir / f"{tenant_key}.png"
    if not sig_path.exists():
        sig_path.write_bytes(base64.b64decode(signature_b64))
    return str(sig_path)


# -----------------------------
# Receipt temp-file helper
# -----------------------------
def _safe_filename(name: str) -> str:
    name = name or "receipt"
    # strip paths
    name = os.path.basename(name)
    # keep ascii-ish
    name = re.sub(r"[^A-Za-z0-9_.-]+", "_", name)
    return name[:120] or "receipt"


async def save_upload_to_tmp(upload: UploadFile) -> str:
    """
    Saves UploadFile to /tmp and returns file path.
    """
    data = await upload.read()
    if not data:
        raise ValueError("Uploaded receipt is empty")

    fn = _safe_filename(upload.filename or "receipt")
    # Ensure we keep extension if provided
    tmp_path = Path("/tmp") / fn
    tmp_path.write_bytes(data)
    return str(tmp_path)


# -----------------------------
# Core pipeline: receipt -> bew_data
# -----------------------------
@dataclass
class BuildResult:
    bew_data: dict
    receipt_path: str
    tenant_key: str


async def build_bew_data_from_upload(
    receipt: UploadFile,
    email_text: str,
    tenant_key: str = "default",
) -> BuildResult:
    """
    1) Saves receipt to /tmp
    2) OCR using ocr_bon(path)
    3) LLM extraction using extract_bewirtungsdaten_gemini(ocr_text, email_text)
    4) Applies tenant defaults (ort + signature)
    5) Applies pragmatic tip defaults
    """
    tenant_key = (tenant_key or "default").strip().lower()
    tenant = get_tenant(tenant_key)

    receipt_path = await save_upload_to_tmp(receipt)

    # OCR expects a file path in your project
    ocr_text = ocr_bon(receipt_path)

    # Extract structured data
    bew_data = extract_bewirtungsdaten_gemini(ocr_text, email_text) or {}
    if not isinstance(bew_data, dict):
        raise RuntimeError("extract_bewirtungsdaten_gemini did not return a dict")

    # ---- Tenant defaults ----
    if not bew_data.get("ort"):
        bew_data["ort"] = tenant.default_city

    # Signature: add signature_path that fill_template() can pick up
    if getattr(tenant, "signature_png_b64", None):
        bew_data["signature_path"] = write_signature_tmp(tenant.signature_png_b64, tenant.tenant_key)

    # ---- Trinkgeld pragmatic ----
    # If no tip: set to 0,00 EUR and make betrag_rechnung = betrag (final amount)
    if not bew_data.get("trinkgeld"):
        bew_data["trinkgeld"] = "0,00 EUR"
        if not bew_data.get("betrag_rechnung"):
            bew_data["betrag_rechnung"] = bew_data.get("betrag", "")

    return BuildResult(bew_data=bew_data, receipt_path=receipt_path, tenant_key=tenant.tenant_key)


# -----------------------------
# Optional: local quick-test (does NOT call your API)
# -----------------------------
if __name__ == "__main__":
    # This block is intentionally minimal; production uses service.py endpoint.
    print("full_agent_gemini.py loaded. Use build_bew_data_from_upload() from service.py.")
