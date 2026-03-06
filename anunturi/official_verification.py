"""
Verificare online a veridicității datelor oficiale (CUI/CIF) pentru membri cu date identificabile.

Surse utilizate (gratuit, date de bază / oficiale):
- SRL (și PFA): termene.ro → gratuit (date de bază)
                listafirme.ro → gratuit (date principale)
- ONG / AF:     portal.just.ro → gratuit (registrul oficial – asociații și fundații)

Pe parcurs: se pot adăuga API-uri sau chei pentru verificare automată.
"""
import json
import re
import ssl
import urllib.error
import urllib.parse
import urllib.request
from typing import Any

# Surse documentate pentru verificare manuală / automată
SOURCES = {
    "srl": [
        ("termene.ro", "https://termene.ro/", "Date de bază – gratuit"),
        ("listafirme.ro", "https://www.listafirme.ro/", "Date principale – gratuit"),
    ],
    "ong": [
        ("portal.just.ro", "https://www.just.ro/registrul-national-ong/", "Registrul oficial – gratuit"),
    ],
}


def normalize_cui(value: str) -> str:
    """Extrage doar cifrele din CUI/CIF (elimină spații, liniuțe)."""
    if not value:
        return ""
    return re.sub(r"\D", "", str(value).strip())


def is_cui_format_valid(cui: str) -> tuple[bool, str]:
    """
    Verifică format CUI/CIF România: 2–10 cifre (de obicei 6–10).
    Returnează (ok, mesaj_eroare).
    """
    digits = normalize_cui(cui)
    if not digits:
        return False, "CUI/CIF este gol."
    if len(digits) < 2 or len(digits) > 10:
        return False, "CUI/CIF trebuie să aibă între 2 și 10 cifre."
    return True, ""


def verify_srl_cui(cui: str, api_key: str | None = None) -> dict[str, Any]:
    """
    Verificare CUI pentru SRL / PFA.
    Surse: termene.ro, listafirme.ro (gratuit).

    Dacă api_key (listafirme.ro) este setat, se încearcă verificare automată via API.
    Altfel se returnează sursele pentru verificare manuală și doar validarea de format.
    """
    normalized = normalize_cui(cui)
    valid_format, err = is_cui_format_valid(cui)
    if not valid_format:
        return {
            "verified": False,
            "error": err,
            "cui_normalized": normalized,
            "sources": [s[0] for s in SOURCES["srl"]],
            "source_urls": [s[1] for s in SOURCES["srl"]],
        }

    result = {
        "verified": False,
        "cui_normalized": normalized,
        "denumire_found": None,
        "sources": [s[0] for s in SOURCES["srl"]],
        "source_urls": [s[1] for s in SOURCES["srl"]],
        "message": "Verificare automată neconfigurată. Verificați manual pe termene.ro sau listafirme.ro.",
    }

    if api_key:
        # ListaFirme.ro API: info-v1.asp cu TaxCode; key în query string
        try:
            url = "https://www.listafirme.ro/api/info-v1.asp"
            url_with_key = f"{url}?key={urllib.parse.quote(api_key)}"
            data = json.dumps({"TaxCode": normalized, "Name": "", "Status": ""}).encode("utf-8")
            req = urllib.request.Request(
                url_with_key,
                data=data,
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            ctx = ssl.create_default_context()
            with urllib.request.urlopen(req, timeout=10, context=ctx) as resp:
                body = resp.read().decode("utf-8", errors="replace")
                info = json.loads(body) if body.strip() else {}
                if info.get("Denumire") or info.get("Name"):
                    result["verified"] = True
                    result["denumire_found"] = info.get("Denumire") or info.get("Name")
                    result["message"] = "CUI găsit în listafirme.ro."
                else:
                    result["message"] = "CUI neînregistrat sau inexistent în listafirme.ro."
        except urllib.error.HTTPError as e:
            result["error"] = f"listafirme.ro: {e.code}"
            result["message"] = "Verificare eșuată (HTTP). Verificați manual pe termene.ro / listafirme.ro."
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as e:
            result["error"] = str(e)
            result["message"] = "Verificare eșuată. Verificați manual pe termene.ro / listafirme.ro."

    return result


def verify_ong_registry(cif: str, numar_registru: str = "", api_key: str | None = None) -> dict[str, Any]:
    """
    Verificare CIF / nr. registru pentru ONG / Asociație / Fundație.
    Sursă: portal.just.ro – Registrul Național ONG (gratuit).

    Registrul just.ro oferă date în PDF/Excel; verificare automată poate fi adăugată pe parcurs.
    Acum: validare format + linkuri pentru verificare manuală.
    """
    normalized_cif = normalize_cui(cif)
    valid_format, err = is_cui_format_valid(cif)
    if not valid_format and not numar_registru:
        return {
            "verified": False,
            "error": err,
            "cif_normalized": normalized_cif,
            "sources": [s[0] for s in SOURCES["ong"]],
            "source_urls": [s[1] for s in SOURCES["ong"]],
            "message": "Completați CIF sau nr. registru și verificați pe portal.just.ro.",
        }

    result = {
        "verified": False,
        "cif_normalized": normalized_cif,
        "numar_registru": (numar_registru or "").strip(),
        "sources": [s[0] for s in SOURCES["ong"]],
        "source_urls": [s[1] for s in SOURCES["ong"]],
        "message": "Verificare manuală: portal.just.ro → Registrul Național ONG.",
    }

    # Pe parcurs: integrare API portal.just.ro dacă devine disponibilă
    if api_key:
        # placeholder pentru viitor
        pass

    return result


def verify_member_official_data(tip_organizatie: str, cui: str, numar_registru: str = "", **kwargs: Any) -> dict[str, Any]:
    """
    Unificat: verifică datele oficiale în funcție de tip (SRL/PFA vs ONG/AF).
    kwargs: listafirme_api_key, just_ro_api_key (opțional).
    """
    cui = (cui or "").strip()
    numar_registru = (numar_registru or "").strip()

    if tip_organizatie in ("srl", "pfa"):
        return verify_srl_cui(cui, api_key=kwargs.get("listafirme_api_key"))
    if tip_organizatie in ("ong", "af"):
        return verify_ong_registry(cif=cui, numar_registru=numar_registru, api_key=kwargs.get("just_ro_api_key"))

    return {
        "verified": False,
        "error": "Tip organizație necunoscut.",
        "message": "Selectați SRL, PFA, ONG sau AF.",
    }
