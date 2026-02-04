import os
import psycopg
from dataclasses import dataclass
from typing import Optional

@dataclass
class Tenant:
    tenant_key: str
    display_name: Optional[str]
    default_city: str
    signature_png_b64: Optional[str]
    reply_from_email: Optional[str]
    template_key: str

def _db_url() -> str:
    url = os.getenv("TENANT_DATABASE_URL", "").strip()
    if not url:
        raise RuntimeError("TENANT_DATABASE_URL is not set")
    return url

def get_tenant(tenant_key: str) -> Tenant:
    tenant_key = (tenant_key or "default").strip().lower()

    with psycopg.connect(_db_url()) as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT tenant_key, display_name, default_city, signature_png_b64, reply_from_email, template_key
                FROM tenants
                WHERE tenant_key = %s
                """,
                (tenant_key,),
            )
            row = cur.fetchone()

    # Fallback: nimm default, wenn tenant nicht existiert
    if not row and tenant_key != "default":
        return get_tenant("default")

    if not row:
        # absoluter Hard-Fallback falls DB leer/kaputt
        return Tenant(
            tenant_key="default",
            display_name="Default Tenant",
            default_city="Berlin",
            signature_png_b64=None,
            reply_from_email=None,
            template_key="default",
        )

    return Tenant(*row)
