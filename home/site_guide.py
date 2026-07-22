"""
Ghid EU-Adopt: potrivire FAQ, refuzuri, fallback Gemini (opțional).
"""

from __future__ import annotations

import json
import logging
import re
import unicodedata
from typing import Any

from django.conf import settings
from django.core.cache import cache

from home.site_guide_faq import (
    REFUSE_MEDICAL,
    REFUSE_NO_MATCH,
    REFUSE_OUT_OF_SCOPE,
    SITE_GUIDE_FAQ,
    SITE_GUIDE_KNOWLEDGE,
    SITE_GUIDE_QUICK_CHIP_IDS,
    SiteGuideFaqEntry,
)

logger = logging.getLogger(__name__)

_MEDICAL_RE = re.compile(
    r"\b(vaccin|vaccinuri|steriliz|medicament|tratament|boli|boala|boală|veterinar|"
    r"doctor|sănătate|sanatate|urgenta|urgență|symptom|simptom|parazit|deparazit|"
    r"cip\b|antirabic|rabie|operat|chirurg|diagnostic)\b",
    re.IGNORECASE,
)

_NUTRITION_RE = re.compile(
    r"\b(nutritie|nutriție|hrana|hrană|mancare|mâncare|dieta|dietă|ce mananc|ce mănânc|"
    r"ce hrană|ce hrana|vitamin|supliment)\b",
    re.IGNORECASE,
)

_FIND_ANIMAL_RE = re.compile(
    r"\b(gasesc|găsesc|gasim|găsim|caut|cauta|caută|filtrez|filtru|unde|cum\s+ajung|"
    r"vreau\s+sa\s+vad|vreau\s+să\s+văd)\b",
    re.IGNORECASE,
)

_OTHER_SPECIES_RE = re.compile(
    r"\b(hamster|hamsteri|iepure|iepuri|porcusor|porcu[sș]or|guineea|cobai|chinchilla|"
    r"papagal|broasc[aă]|testoas[aă]|rozatoare|rozătoare|altele)\b",
    re.IGNORECASE,
)

_INTERNAL_RE = re.compile(
    r"\b(api|database|db\b|django|admin|render|smtp|server|cod sursa|cod sursă|"
    r"migrare|github|\.env|token oauth|backend)\b",
    re.IGNORECASE,
)

_LEGAL_MERIT_RE = re.compile(
    r"\b(merit|legal|ilegal|contract|proprietar real|garantat|sigur primesc)\b",
    re.IGNORECASE,
)


def is_site_guide_enabled() -> bool:
    return bool(getattr(settings, "SITE_GUIDE_ENABLED", False))


def is_site_guide_path(path: str) -> bool:
    p = (path or "/").split("?", 1)[0].rstrip("/") or "/"
    # Vizibil pe tot site-ul (inclusiv pagini de login/signup), în afara adminului.
    if p.startswith("/admin"):
        return False
    if p.startswith("/__debug__"):
        return False
    if p.startswith("/"):
        return True
    return False


def is_gemini_fallback_live() -> bool:
    if not getattr(settings, "SITE_GUIDE_GEMINI_ENABLED", False):
        return False
    return bool(getattr(settings, "EUADOPT_GEMINI_API_KEY", "").strip())


def get_quick_chip_entries() -> list[SiteGuideFaqEntry]:
    by_id = {e.id: e for e in SITE_GUIDE_FAQ}
    out: list[SiteGuideFaqEntry] = []
    for cid in SITE_GUIDE_QUICK_CHIP_IDS:
        if cid in by_id:
            out.append(by_id[cid])
    return out


def _normalize(text: str) -> str:
    t = (text or "").strip().lower()
    t = unicodedata.normalize("NFD", t)
    t = "".join(c for c in t if unicodedata.category(c) != "Mn")
    return t


def _detect_refusal(question: str) -> str | None:
    q = _normalize(question)
    if not q:
        return None
    if _MEDICAL_RE.search(q):
        return REFUSE_MEDICAL
    if _NUTRITION_RE.search(q):
        return (
            "Ghidul EU-Adopt te ajută doar cu **navigarea pe site**, nu cu sfaturi de nutriție sau dietă.\n\n"
            "Pentru un animal listat: deschide **fișa** pe Prietenul tău și folosește **mesajele** către adăpost.\n"
            "Pentru întrebări generale despre site: întreabă cum folosești **Filtre** sau tabul **Altele**."
        )
    if _INTERNAL_RE.search(q):
        return REFUSE_OUT_OF_SCOPE
    if _LEGAL_MERIT_RE.search(q):
        return (
            "Fiecare adopție este evaluată de adăpost sau asociație — ghidul nu poate spune dacă "
            "primești un anumit animal.\n\n"
            "Trimite **cererea de adopție** pe fișă și discutați prin mesaje după accept."
        )
    return None


def _score_faq(question_norm: str, entry: SiteGuideFaqEntry) -> int:
    score = 0
    for kw in entry.keywords:
        kn = _normalize(kw)
        if kn in question_norm:
            score += max(2, len(kn.split()))
    title_norm = _normalize(entry.title)
    for word in title_norm.split():
        if len(word) > 3 and word in question_norm:
            score += 1
    return score


_FAQ_CONTEXT_BOOST: dict[str, tuple[str, ...]] = {
    "servicii_ce": ("servicii", "veterinar", "grooming", "cabinet", "salon", "magazin partener"),
    "transport_ce": ("transport", "curier", "deplasare"),
    "pt_specie_altele": (
        "hamster", "iepure", "iepuri", "altele", "porcusor", "cobai", "gasesc", "găsesc", "caut",
    ),
    "pt_cautare": (
        "prietenul", "animale", "caini", "câini", "pisici", "grila", "card", "filtrez", "filtru",
    ),
    "pt_unde": ("lista animale",),
    "shop_ce": ("shop", "magazin", "produs"),
    "ilove_ce": ("i love", "ilove", "favorite", "inimioara", "inimioară"),
    "mypet_ce": ("mypet", "my pet", "adapost", "adăpost"),
}


def _intent_boost(question_norm: str, entry_id: str) -> int:
    """Prioritizează răspunsul PT / Altele la întrebări de tip „cum găsesc hamster”."""
    boost = 0
    if entry_id == "pt_specie_altele" and _OTHER_SPECIES_RE.search(question_norm):
        boost += 10
        if _FIND_ANIMAL_RE.search(question_norm):
            boost += 8
    if entry_id == "pt_cautare" and _FIND_ANIMAL_RE.search(question_norm):
        boost += 4
    if entry_id == "pt_unde" and _OTHER_SPECIES_RE.search(question_norm):
        boost -= 6
    return boost


def match_faq(question: str, *, faq_id: str | None = None) -> SiteGuideFaqEntry | None:
    if faq_id:
        for entry in SITE_GUIDE_FAQ:
            if entry.id == faq_id:
                return entry
        return None

    qn = _normalize(question)
    if not qn:
        return None

    best: SiteGuideFaqEntry | None = None
    best_score = 0
    for entry in SITE_GUIDE_FAQ:
        s = _score_faq(qn, entry)
        for ctx in _FAQ_CONTEXT_BOOST.get(entry.id, ()):
            if ctx in qn:
                s += 5
                break
        s += _intent_boost(qn, entry.id)
        if s > best_score:
            best_score = s
            best = entry

    if best and best_score >= 2:
        return best
    return None


def _rate_limit_key(ip: str) -> str:
    return f"euadopt:site_guide:rl:{ip}"


def check_rate_limit(ip: str) -> bool:
    """True dacă mai are voie."""
    limit = int(getattr(settings, "SITE_GUIDE_RATE_LIMIT_PER_HOUR", 30))
    key = _rate_limit_key(ip or "unknown")
    count = cache.get(key, 0)
    return count < limit


def bump_rate_limit(ip: str) -> None:
    key = _rate_limit_key(ip or "unknown")
    count = cache.get(key, 0)
    cache.set(key, count + 1, 3600)


def _page_context_hint(page_path: str) -> str:
    p = (page_path or "").strip().rstrip("/") or "/"
    hints = {
        "/": "Utilizatorul e pe Acasă.",
        "/pets": "Utilizatorul e pe Prietenul tău — menționează filtrele P4 (Județ, Talie, Vârstă, Sex, specie).",
        "/servicii": "Utilizatorul e pe Servicii — menționează Județ, Oraș/Loc, specie, taburi Veterinare/Magazine/Saloane.",
        "/shop": "Utilizatorul e pe Shop.",
        "/transport": "Utilizatorul e pe Transport — descrie pașii formularului.",
        "/i-love": "Utilizatorul e pe I Love — lista de favorite.",
        "/mypet": "Utilizatorul e pe MyPet — panou adăpost/ONG.",
    }
    if p.startswith("/pets/") and p != "/pets":
        return "Utilizatorul e pe fișa unui animal."
    return hints.get(p, "")


def _gemini_system_prompt(page_path: str = "") -> str:
    page_hint = _page_context_hint(page_path)
    page_block = f"\nContext pagină: {page_hint}\n" if page_hint else ""
    return (
        "Ești Ghidul EU-Adopt — asistent pentru navigarea pe site.\n"
        "Răspunde DOAR în română, clar și concret (max ~200 cuvinte).\n"
        "Include pași numerotați când e util; numește exact butoanele, taburile și filtrele din UI.\n"
        "NU da sfaturi medicale, veterinare, de nutriție/dietă sau legale. NU dezvălui cod, API-uri sau detalii interne.\n"
        "Dacă întrebarea e despre găsirea unui animal (ex. hamster, iepure): meniu **Prietenul tău** → tab **Altele** → **Filtre**.\n"
        "Dacă întrebarea e medicală, redirecționează spre mesajele de pe fișa animalului sau Contact.\n"
        "Folosește nume de meniu: Acasă, Prietenul tău, I Love, MyPet, Servicii, Shop, Transport, Contact.\n"
        f"{page_block}\n"
        "Bază de cunoștințe site (folosește-o pentru detalii exacte):\n"
        f"{SITE_GUIDE_KNOWLEDGE.strip()}"
    )


def ask_gemini(question: str, page_path: str = "") -> str | None:
    api_key = getattr(settings, "EUADOPT_GEMINI_API_KEY", "").strip()
    if not api_key:
        return None

    primary = getattr(settings, "SITE_GUIDE_GEMINI_MODEL", "gemini-2.5-flash").strip()
    fallbacks = [primary]
    for alt in ("gemini-2.5-flash", "gemini-2.5-flash-lite", "gemini-2.0-flash"):
        if alt not in fallbacks:
            fallbacks.append(alt)

    user_block = question.strip()
    if page_path:
        user_block = f"[Pagină curentă: {page_path}]\n{user_block}"

    payload = {
        "system_instruction": {"parts": [{"text": _gemini_system_prompt(page_path)}]},
        "contents": [{"role": "user", "parts": [{"text": user_block}]}],
        "generationConfig": {
            "temperature": 0.3,
            "maxOutputTokens": 650,
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
            with urllib.request.urlopen(req, timeout=25) as resp:
                data = json.loads(resp.read().decode("utf-8"))
            candidates = data.get("candidates") or []
            if not candidates:
                continue
            parts = (candidates[0].get("content") or {}).get("parts") or []
            text = "".join(p.get("text", "") for p in parts).strip()
            if text:
                return text
        except urllib.error.HTTPError as exc:
            body = exc.read().decode("utf-8", errors="replace")[:400]
            logger.warning("Gemini model %s failed HTTP %s: %s", model, exc.code, body)
            if exc.code in (429, 404, 503):
                continue
            logger.exception("Gemini site guide request failed")
            return None
        except Exception:
            logger.exception("Gemini site guide request failed for model %s", model)
            continue
    return None


def answer_question(
    question: str,
    *,
    faq_id: str | None = None,
    page_path: str = "",
) -> dict[str, Any]:
    """
    Returnează dict: answer, source (faq|refuse|gemini|fallback), faq_id optional.
    """
    refusal = _detect_refusal(question)
    if refusal:
        return {"answer": refusal, "source": "refuse"}

    entry = match_faq(question, faq_id=faq_id)
    if entry:
        return {"answer": entry.answer, "source": "faq", "faq_id": entry.id, "title": entry.title}

    if is_gemini_fallback_live():
        gemini_text = ask_gemini(question, page_path=page_path)
        if gemini_text:
            return {"answer": gemini_text, "source": "gemini"}

    return {"answer": REFUSE_NO_MATCH, "source": "fallback"}
