"""
Contacte organe competente pe județ — semnalări abuz.

Listele reale DSVSA / BPA se completează ulterior.
Până atunci: email gol → fallback Poliție județeană (dacă există) cu mențiunea
„Către Biroul de Protecție a Animalelor”; altfel sesizarea rămâne înregistrată
și se notifică inbox-ul EU-Adopt (pending).
"""

from __future__ import annotations

from dataclasses import dataclass

from home.campanii_ro import campanii_judete


DEST_DSVSA = "dsvsa"
DEST_BPA = "bpa"
DEST_BOTH = "both"
DEST_CHOICES = (
    (DEST_DSVSA, "DSVSA"),
    (DEST_BPA, "Poliția Animalelor (BPA)"),
    (DEST_BOTH, "Ambele (DSVSA + Poliția Animalelor)"),
)


@dataclass(frozen=True)
class AbuzContactRow:
    code: str
    name: str
    slug: str
    dsvsa_email: str = ""
    bpa_email: str = ""
    # Fallback: poliție județeană — folosit când lipsește BPA
    politie_judeteana_email: str = ""


# Completare ulterioară: emailuri reale pe cod județ (AB, CJ, …).
# Chei: dsvsa | bpa | politie
_MANUAL_CONTACTS: dict[str, dict[str, str]] = {
    # Exemplu (dezactivat):
    # "NT": {"dsvsa": "office@dsvsa-neamt.example", "bpa": "", "politie": "bjneamt@politiaromana.ro"},
}


def abuz_contact_rows() -> list[AbuzContactRow]:
    out: list[AbuzContactRow] = []
    for j in campanii_judete():
        code = (j.code or "").strip().upper()
        if not code:
            continue
        manual = _MANUAL_CONTACTS.get(code) or {}
        out.append(
            AbuzContactRow(
                code=code,
                name=j.name,
                slug=j.slug,
                dsvsa_email=(manual.get("dsvsa") or "").strip(),
                bpa_email=(manual.get("bpa") or "").strip(),
                politie_judeteana_email=(manual.get("politie") or "").strip(),
            )
        )
    return out


def abuz_contact_by_slug(slug: str) -> AbuzContactRow | None:
    key = (slug or "").strip().lower()
    for row in abuz_contact_rows():
        if (row.slug or "").strip().lower() == key:
            return row
    return None


def resolve_abuz_recipients(row: AbuzContactRow, destinatie: str) -> list[dict]:
    """
    Returnează lista {email, label, attention_line} pentru trimitere.
    attention_line = text scurt de pus în corp (ex. Către Biroul…).
    """
    dest = (destinatie or "").strip().lower()
    want_dsvsa = dest in (DEST_DSVSA, DEST_BOTH)
    want_bpa = dest in (DEST_BPA, DEST_BOTH)
    recipients: list[dict] = []

    if want_dsvsa:
        email = (row.dsvsa_email or "").strip()
        if email:
            recipients.append(
                {
                    "email": email,
                    "label": "DSVSA",
                    "attention_line": f"Către DSVSA — județul {row.name}",
                }
            )
        else:
            recipients.append(
                {
                    "email": "",
                    "label": "DSVSA",
                    "attention_line": f"Către DSVSA — județul {row.name}",
                    "pending": True,
                }
            )

    if want_bpa:
        bpa = (row.bpa_email or "").strip()
        politie = (row.politie_judeteana_email or "").strip()
        if bpa:
            recipients.append(
                {
                    "email": bpa,
                    "label": "Poliția Animalelor (BPA)",
                    "attention_line": f"Către Biroul de Protecție a Animalelor — județul {row.name}",
                }
            )
        elif politie:
            recipients.append(
                {
                    "email": politie,
                    "label": "Poliția județeană (fallback BPA)",
                    "attention_line": (
                        f"Către Biroul de Protecție a Animalelor — "
                        f"Poliția Județeană {row.name}"
                    ),
                }
            )
        else:
            recipients.append(
                {
                    "email": "",
                    "label": "Poliția Animalelor / Poliție județeană",
                    "attention_line": (
                        f"Către Biroul de Protecție a Animalelor — județul {row.name}"
                    ),
                    "pending": True,
                }
            )

    return recipients
