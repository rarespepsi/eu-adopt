#!/usr/bin/env python3
"""Generate EU UI label packs via Gemini (variant B languages)."""
from __future__ import annotations

import json
import os
import re
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

# Load .env without Django
try:
    from dotenv import load_dotenv

    load_dotenv(ROOT / ".env")
except Exception:
    pass

from home.eu_ui_labels import _EN  # noqa: E402

TARGET_LANGS = ("de", "fr", "es", "it", "pl", "nl", "pt", "ro")
LANG_NAMES = {
    "de": "German",
    "fr": "French",
    "es": "Spanish",
    "it": "Italian",
    "pl": "Polish",
    "nl": "Dutch",
    "pt": "Portuguese (European)",
    "ro": "Romanian",
}
OUT = ROOT / "home" / "eu_ui_labels_i18n.json"
BATCH = 50
PLACEHOLDER_RE = re.compile(r"\{[a-zA-Z0-9_]+\}")


def _api_key() -> str:
    return (os.environ.get("EUADOPT_GEMINI_API_KEY") or "").strip()


def _model() -> str:
    return (os.environ.get("EUADOPT_SITE_GUIDE_GEMINI_MODEL") or "gemini-2.5-flash").strip()


def _gemini_json(prompt: str) -> dict:
    key = _api_key()
    if not key:
        raise RuntimeError("EUADOPT_GEMINI_API_KEY missing")
    url = (
        f"https://generativelanguage.googleapis.com/v1beta/models/{_model()}:"
        f"generateContent?key={key}"
    )
    body = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {
            "temperature": 0.1,
            "responseMimeType": "application/json",
        },
    }
    data = json.dumps(body).encode("utf-8")
    req = urllib.request.Request(
        url, data=data, headers={"Content-Type": "application/json"}, method="POST"
    )
    last_err: Exception | None = None
    for attempt in range(8):
        try:
            with urllib.request.urlopen(req, timeout=120) as resp:
                raw = json.loads(resp.read().decode("utf-8"))
            text = (
                raw.get("candidates", [{}])[0]
                .get("content", {})
                .get("parts", [{}])[0]
                .get("text", "")
            )
            return json.loads(text)
        except urllib.error.HTTPError as exc:
            last_err = exc
            wait = 8 * (attempt + 1) if exc.code == 429 else 2 * (attempt + 1)
            print(f"    HTTP {exc.code}, sleep {wait}s", flush=True)
            time.sleep(wait)
            # rebuild request body for retry
            req = urllib.request.Request(
                url, data=data, headers={"Content-Type": "application/json"}, method="POST"
            )
        except Exception as exc:  # noqa: BLE001
            last_err = exc
            time.sleep(2 * (attempt + 1))
            req = urllib.request.Request(
                url, data=data, headers={"Content-Type": "application/json"}, method="POST"
            )
    raise RuntimeError(f"Gemini failed: {last_err}")


def translate_chunk(items: dict[str, str], lang: str) -> dict[str, str]:
    lang_name = LANG_NAMES[lang]
    prompt = (
        f"Translate these UI strings from English to {lang_name}.\n"
        "Return a JSON object with THE SAME keys and translated string values.\n"
        "Rules:\n"
        "- Keep placeholders like {n}, {name}, {pet}, {imp}, {mins}, {price} EXACTLY unchanged.\n"
        "- Keep brand names: EU-ADOPT, EU-Adopt, MyPet, I Love, A2.\n"
        "- Keep email addresses and URLs unchanged.\n"
        "- Natural UI tone for a pet-adoption website.\n"
        "- Do not add extra keys.\n\n"
        f"{json.dumps(items, ensure_ascii=False)}"
    )
    out = _gemini_json(prompt)
    if not isinstance(out, dict):
        raise RuntimeError("Gemini did not return an object")
    fixed: dict[str, str] = {}
    for k, src in items.items():
        val = out.get(k)
        if not isinstance(val, str) or not val.strip():
            fixed[k] = src
            continue
        # Ensure placeholders survive
        for ph in PLACEHOLDER_RE.findall(src):
            if ph not in val:
                val = src
                break
        fixed[k] = val
    return fixed


def main() -> None:
    existing: dict[str, dict[str, str]] = {}
    if OUT.exists():
        existing = json.loads(OUT.read_text(encoding="utf-8"))

    keys = list(_EN.keys())
    for lang in TARGET_LANGS:
        pack = dict(existing.get(lang, {}))
        todo = [k for k in keys if k not in pack or not str(pack.get(k, "")).strip()]
        print(f"=== {lang}: {len(todo)} remaining ===", flush=True)
        for i in range(0, len(todo), BATCH):
            chunk_keys = todo[i : i + BATCH]
            chunk = {k: _EN[k] for k in chunk_keys}
            try:
                translated = translate_chunk(chunk, lang)
            except Exception as exc:  # noqa: BLE001
                print(f"  retry after error: {exc}", flush=True)
                time.sleep(3)
                translated = translate_chunk(chunk, lang)
            pack.update(translated)
            existing[lang] = pack
            OUT.write_text(json.dumps(existing, ensure_ascii=False, indent=2), encoding="utf-8")
            print(f"  {lang}: {min(i + BATCH, len(todo))}/{len(todo)}", flush=True)
            time.sleep(1.2)
        print(f"DONE {lang}: {len(pack)}", flush=True)

    print(f"Wrote {OUT}", flush=True)


if __name__ == "__main__":
    main()
