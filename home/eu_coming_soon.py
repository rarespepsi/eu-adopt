"""Texte Coming soon pe hub EU — limbi din TLD-uri active (EN/DE/FR/ES)."""
from __future__ import annotations

from django.conf import settings

# Limbi corespunzătoare domeniilor active: .com=EN, .de, .fr, .es
COMING_SOON_I18N: dict[str, dict[str, str]] = {
    "en": {
        "title": "EU-Adopt — Coming soon",
        "heading": "EU-Adopt — coming soon",
        "body": (
            "This international site is not open to the public yet. "
            "The main site is available in Romania."
        ),
        "go_ro": "Go to eu-adopt.ro",
        "staff_login": "Staff login",
    },
    "de": {
        "title": "EU-Adopt — Demnächst",
        "heading": "EU-Adopt — demnächst verfügbar",
        "body": (
            "Diese internationale Website ist noch nicht für die Öffentlichkeit geöffnet. "
            "Die Hauptseite ist in Rumänien verfügbar."
        ),
        "go_ro": "Zu eu-adopt.ro",
        "staff_login": "Staff-Login",
    },
    "fr": {
        "title": "EU-Adopt — Bientôt disponible",
        "heading": "EU-Adopt — bientôt disponible",
        "body": (
            "Ce site international n'est pas encore ouvert au public. "
            "Le site principal est disponible en Roumanie."
        ),
        "go_ro": "Aller sur eu-adopt.ro",
        "staff_login": "Connexion staff",
    },
    "es": {
        "title": "EU-Adopt — Próximamente",
        "heading": "EU-Adopt — próximamente",
        "body": (
            "Este sitio internacional aún no está abierto al público. "
            "El sitio principal está disponible en Rumanía."
        ),
        "go_ro": "Ir a eu-adopt.ro",
        "staff_login": "Acceso staff",
    },
}

COMING_SOON_LANGS = frozenset(COMING_SOON_I18N.keys())


def coming_soon_lang_for_request(request) -> str:
    """Limba Coming soon: TLD țară; pe .com aceleași reguli ca UI (EN implicit)."""
    try:
        from home.eu_site import forced_locale_for_host, is_eu_hub_host, pick_language_for_hub

        forced = forced_locale_for_host(request.get_host())
        if forced in COMING_SOON_LANGS:
            return forced
        if is_eu_hub_host(request.get_host()):
            picked = pick_language_for_hub(request)
            return picked if picked in COMING_SOON_LANGS else "en"
    except Exception:
        pass

    get_lang = ""
    try:
        get_lang = (request.GET.get("eu_lang") or "").strip().lower()
    except Exception:
        pass
    if get_lang in COMING_SOON_LANGS:
        return get_lang

    cookie_name = getattr(settings, "LANGUAGE_COOKIE_NAME", "django_language")
    cookie_lang = (request.COOKIES.get(cookie_name) or "").strip().lower()
    if cookie_lang in COMING_SOON_LANGS:
        return cookie_lang

    session = getattr(request, "session", None)
    if session is not None:
        sess = (session.get("django_language") or "").strip().lower()
        if sess in COMING_SOON_LANGS:
            return sess

    code = (getattr(request, "LANGUAGE_CODE", None) or "").strip().lower().split("-")[0]
    if code in COMING_SOON_LANGS:
        return code

    return "en"


def coming_soon_copy(request) -> dict[str, str]:
    lang = coming_soon_lang_for_request(request)
    pack = COMING_SOON_I18N[lang]
    return {"lang": lang, **pack}
