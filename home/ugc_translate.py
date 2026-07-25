"""
Traducere UGC (descrieri animal, mesaje pet) — afișare pe .com / bidirecțional mesaje.

Stochează în DB textul original; la afișare traduce către limba vizitatorului
(Gemini + cache Django). Fără cheie API → returnează originalul.
"""

from __future__ import annotations

import hashlib
import json
import logging
import re
from typing import Any

from django.conf import settings
from django.core.cache import cache

logger = logging.getLogger(__name__)

_RO_CHARS = re.compile(r"[ăâîșțĂÂÎȘŢşţ]", re.UNICODE)
_RO_MARKERS = re.compile(
    r"(?:"
    r"[ăâîșțĂÂÎȘŢşţ]|"
    r"\b(?:si|sau|pentru|vreau|adopta|adoptie|adopție|caine|cainele|pisic|"
    r"multumesc|buna|salut|sunt|acest|aceasta|animale|anunt|proprietar|"
    r"va\s+rog|te\s+rog)\b"
    r")",
    re.IGNORECASE | re.UNICODE,
)
_CACHE_TTL = 60 * 60 * 24 * 30  # 30 zile
_LANG_NAMES = {
    "en": "English",
    "ro": "Romanian",
    "de": "German",
    "fr": "French",
    "es": "Spanish",
    "it": "Italian",
}


def ugc_translate_enabled() -> bool:
    raw = getattr(settings, "UGC_TRANSLATE_ENABLED", True)
    if not raw:
        return False
    return bool(getattr(settings, "EUADOPT_GEMINI_API_KEY", "").strip())


def display_lang_for_request(request: Any) -> str:
    """Limbă țintă pentru vizualizare: pe EU site → eu_site_lang (implicit en); pe .ro → ro."""
    if getattr(request, "eu_site_active", False):
        lang = (getattr(request, "eu_site_lang", None) or "en").strip().lower()[:5]
        if lang.startswith("en"):
            return "en"
        if len(lang) >= 2:
            return lang[:2]
        return "en"
    return "ro"


def _looks_romanian(text: str) -> bool:
    return bool(_RO_MARKERS.search(text or ""))


def _looks_like_target(text: str, target_lang: str) -> bool:
    """Skip MT când textul pare deja în limba țintă (inclusiv RO fără diacritice)."""
    t = (text or "").strip()
    if not t or len(t) < 3:
        return True
    is_ro = _looks_romanian(t)
    tl = (target_lang or "").lower()[:2]
    if tl == "ro":
        return is_ro
    # EN / alte limbi EU: skip dacă nu arată a română
    return not is_ro


def _cache_key(text: str, target_lang: str) -> str:
    digest = hashlib.sha256(f"{target_lang}\n{text}".encode("utf-8")).hexdigest()[:40]
    return f"ugc_tr:v1:{target_lang}:{digest}"


def _gemini_translate(text: str, target_lang: str) -> str | None:
    api_key = getattr(settings, "EUADOPT_GEMINI_API_KEY", "").strip()
    if not api_key:
        return None

    lang_name = _LANG_NAMES.get(target_lang[:2], target_lang)
    primary = getattr(settings, "SITE_GUIDE_GEMINI_MODEL", "gemini-2.5-flash").strip()
    fallbacks = [primary]
    for alt in ("gemini-2.5-flash", "gemini-2.5-flash-lite", "gemini-2.0-flash"):
        if alt not in fallbacks:
            fallbacks.append(alt)

    system = (
        f"You are a precise translator for a pet-adoption platform. "
        f"Translate the user text into {lang_name}. "
        "Return ONLY the translation, no quotes, no commentary. "
        "Keep names, places, and medical terms accurate. "
        "If the text is already in the target language, return it unchanged."
    )
    payload = {
        "system_instruction": {"parts": [{"text": system}]},
        "contents": [{"role": "user", "parts": [{"text": text}]}],
        "generationConfig": {
            "temperature": 0.1,
            "maxOutputTokens": 2048,
        },
    }

    import urllib.error
    import urllib.request

    for model in fallbacks:
        url = (
            f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
            f"?key={api_key}"
        )
        try:
            req = urllib.request.Request(
                url,
                data=json.dumps(payload).encode("utf-8"),
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=20) as resp:
                data = json.loads(resp.read().decode("utf-8"))
            candidates = data.get("candidates") or []
            if not candidates:
                continue
            parts = (candidates[0].get("content") or {}).get("parts") or []
            out = "".join(p.get("text", "") for p in parts).strip()
            if out:
                return out
        except urllib.error.HTTPError as exc:
            body = exc.read().decode("utf-8", errors="replace")[:300]
            logger.warning("UGC translate Gemini %s HTTP %s: %s", model, exc.code, body)
            if exc.code in (429, 404, 503):
                continue
            return None
        except Exception:
            logger.exception("UGC translate Gemini failed for model %s", model)
            continue
    return None


def translate_text(text: str, target_lang: str) -> str:
    """
    Traduce `text` către `target_lang` (ex. en, ro).
    Returnează originalul dacă MT e dezactivat, text scurt, sau eșec.
    """
    raw = (text or "").strip()
    if not raw:
        return text or ""
    tl = (target_lang or "en").strip().lower()[:2] or "en"
    if not ugc_translate_enabled():
        return text
    if _looks_like_target(raw, tl):
        return text

    key = _cache_key(raw, tl)
    cached = cache.get(key)
    if isinstance(cached, str) and cached:
        return cached

    translated = _gemini_translate(raw, tl)
    if not translated:
        return text
    cache.set(key, translated, _CACHE_TTL)
    return translated


def body_for_viewer(text: str, request: Any) -> str:
    """Mesaj pet: afișează în limba vizitatorului (bidirecțional .ro ↔ .com)."""
    return translate_text(text, display_lang_for_request(request))


def translate_pet_fields_for_display(fields: dict[str, Any], request: Any) -> dict[str, Any]:
    """
    Pe site EU (.com): traduce câmpurile UGC ale fișei către limba site-ului.
    Pe .ro: lasă neschimbat (mesajele folosesc body_for_viewer separat).
    """
    if not getattr(request, "eu_site_active", False):
        return fields
    if not ugc_translate_enabled():
        return fields
    lang = display_lang_for_request(request)
    out = dict(fields)
    for key in ("cine_sunt", "detalii_animal", "probleme_medicale", "descriere"):
        val = out.get(key)
        if isinstance(val, str) and val.strip():
            out[key] = translate_text(val, lang)
    return out
