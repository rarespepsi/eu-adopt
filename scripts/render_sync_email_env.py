#!/usr/bin/env python3
"""
Sincronizează variabilele SMTP din .env local către Render (Environment).

Utilizare (o singură dată, din rădăcina proiectului):
  set RENDER_API_KEY=rnd_xxxx          # Render Dashboard → Account Settings → API Keys
  set RENDER_SERVICE_ID=srv_xxxx       # Service → Settings → ID din URL sau Overview
  python scripts/render_sync_email_env.py

Nu comite API key-ul. Parola Zoho rămâne doar în .env local și pe Render.
"""

from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ENV_FILE = ROOT / ".env"

EMAIL_KEYS = (
    "EMAIL_HOST",
    "EMAIL_PORT",
    "EMAIL_HOST_USER",
    "EMAIL_HOST_PASSWORD",
    "EMAIL_USE_TLS",
    "EMAIL_USE_SSL",
    "DEFAULT_FROM_EMAIL",
)


def load_dotenv(path: Path) -> dict[str, str]:
    out: dict[str, str] = {}
    if not path.is_file():
        return out
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, _, v = line.partition("=")
        out[k.strip()] = v.strip()
    return out


def main() -> int:
    api_key = (os.environ.get("RENDER_API_KEY") or "").strip()
    service_id = (os.environ.get("RENDER_SERVICE_ID") or "").strip()
    if not api_key or not service_id:
        print(
            "Lipsește RENDER_API_KEY sau RENDER_SERVICE_ID.\n"
            "Render → Account Settings → API Keys\n"
            "Render → serviciul EU-Adopt → Settings (ID în URL: srv-...)\n"
            "Apoi rulează din nou acest script.",
            file=sys.stderr,
        )
        return 1

    local = load_dotenv(ENV_FILE)
    missing = [k for k in EMAIL_KEYS if not (local.get(k) or "").strip()]
    if missing:
        print(f"Lipsesc în {ENV_FILE}: {', '.join(missing)}", file=sys.stderr)
        return 1
    if local.get("EMAIL_HOST_PASSWORD", "").strip() in ("", "PAROLA_ZOHO_TEMP"):
        print("EMAIL_HOST_PASSWORD încă e placeholder în .env.", file=sys.stderr)
        return 1

    # Render API: PUT env vars for service (bulk update pattern via individual env-var API)
  # https://api.render.com/v1/services/{serviceId}/env-vars
    url = f"https://api.render.com/v1/services/{service_id}/env-vars"
    payload = [{"key": k, "value": local[k]} for k in EMAIL_KEYS]

    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        },
        method="PUT",
    )
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            body = resp.read().decode("utf-8", errors="replace")
            print(f"OK ({resp.status}): variabile SMTP setate pe Render pentru {service_id}.")
            if body.strip():
                print(body[:500])
    except urllib.error.HTTPError as e:
        err = e.read().decode("utf-8", errors="replace")
        print(f"Eroare HTTP {e.code}: {err}", file=sys.stderr)
        print(
            "\nDacă PUT nu e suportat, adaugă manual în Render → Environment:\n"
            + "\n".join(f"  {k}=..." for k in EMAIL_KEYS),
            file=sys.stderr,
        )
        return 1
    print("Redeploy: Render poate reporni automat serviciul după schimbarea env.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
