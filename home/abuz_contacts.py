"""
Contacte organe competente pe județ — semnalări abuz.

DSVSA: office-{judet}@ansvsa.ro (ANSVSA / site-uri *.dsvsa.ro).
BPA / poliție: cabinet@{cod}.politiaromana.ro; București: bpa@b.politiaromana.ro.
La BPA fără adresă dedicată: cabinet IPJ + mențiune „Către Biroul de Protecție a Animalelor”.
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
    # Fallback: poliție județeană — folosit când lipsește BPA dedicat
    politie_judeteana_email: str = ""


# Emailuri pe cod auto (AB, CJ, B, …).
_MANUAL_CONTACTS: dict[str, dict[str, str]] = {
    "AB": {
        "dsvsa": "office-alba@ansvsa.ro",
        "politie": "cabinet@ab.politiaromana.ro",
    },
    "AR": {
        "dsvsa": "office-arad@ansvsa.ro",
        "politie": "cabinet@ar.politiaromana.ro",
    },
    "AG": {
        "dsvsa": "office-arges@ansvsa.ro",
        "politie": "cabinet@ag.politiaromana.ro",
    },
    "BC": {
        "dsvsa": "office-bacau@ansvsa.ro",
        "politie": "cabinet@bc.politiaromana.ro",
    },
    "BH": {
        "dsvsa": "office-bihor@ansvsa.ro",
        "politie": "cabinet@bh.politiaromana.ro",
    },
    "BN": {
        "dsvsa": "office-bistrita-nasaud@ansvsa.ro",
        "politie": "cabinet@bn.politiaromana.ro",
    },
    "BT": {
        "dsvsa": "office-botosani@ansvsa.ro",
        "politie": "cabinet@bt.politiaromana.ro",
    },
    "BR": {
        "dsvsa": "office-braila@ansvsa.ro",
        "politie": "cabinet@br.politiaromana.ro",
    },
    "BV": {
        "dsvsa": "office-brasov@ansvsa.ro",
        "politie": "cabinet@bv.politiaromana.ro",
    },
    "B": {
        "dsvsa": "office-bucuresti@ansvsa.ro",
        "bpa": "bpa@b.politiaromana.ro",
        "politie": "cabinet@b.politiaromana.ro",
    },
    "BZ": {
        "dsvsa": "office-buzau@ansvsa.ro",
        "politie": "cabinet@bz.politiaromana.ro",
    },
    "CL": {
        "dsvsa": "office-calarasi@ansvsa.ro",
        "politie": "cabinet@cl.politiaromana.ro",
    },
    "CS": {
        "dsvsa": "office-caras-severin@ansvsa.ro",
        "politie": "cabinet@cs.politiaromana.ro",
    },
    "CJ": {
        "dsvsa": "office-cluj@ansvsa.ro",
        "politie": "cabinet@cj.politiaromana.ro",
    },
    "CT": {
        "dsvsa": "office-constanta@ansvsa.ro",
        "politie": "cabinet@ct.politiaromana.ro",
    },
    "CV": {
        "dsvsa": "office-covasna@ansvsa.ro",
        "politie": "cabinet@cv.politiaromana.ro",
    },
    "DB": {
        "dsvsa": "office-dambovita@ansvsa.ro",
        "politie": "cabinet@db.politiaromana.ro",
    },
    "DJ": {
        "dsvsa": "office-dolj@ansvsa.ro",
        "politie": "cabinet@dj.politiaromana.ro",
    },
    "GL": {
        "dsvsa": "office-galati@ansvsa.ro",
        "politie": "cabinet@gl.politiaromana.ro",
    },
    "GR": {
        "dsvsa": "office-giurgiu@ansvsa.ro",
        "politie": "cabinet@gr.politiaromana.ro",
    },
    "GJ": {
        "dsvsa": "office-gorj@ansvsa.ro",
        "politie": "cabinet@gj.politiaromana.ro",
    },
    "HR": {
        "dsvsa": "office-harghita@ansvsa.ro",
        "politie": "cabinet@hr.politiaromana.ro",
    },
    "HD": {
        "dsvsa": "office-hunedoara@ansvsa.ro",
        "politie": "cabinet@hd.politiaromana.ro",
    },
    "IL": {
        "dsvsa": "office-ialomita@ansvsa.ro",
        "politie": "cabinet@il.politiaromana.ro",
    },
    "IS": {
        "dsvsa": "office-iasi@ansvsa.ro",
        "politie": "cabinet@is.politiaromana.ro",
    },
    "IF": {
        "dsvsa": "office-ilfov@ansvsa.ro",
        "politie": "cabinet@if.politiaromana.ro",
    },
    "MM": {
        "dsvsa": "office-maramures@ansvsa.ro",
        "politie": "cabinet@mm.politiaromana.ro",
    },
    "MH": {
        "dsvsa": "office-mehedinti@ansvsa.ro",
        "politie": "cabinet@mh.politiaromana.ro",
    },
    "MS": {
        "dsvsa": "office-mures@ansvsa.ro",
        "politie": "cabinet@ms.politiaromana.ro",
    },
    "NT": {
        "dsvsa": "office-neamt@ansvsa.ro",
        "politie": "cabinet@nt.politiaromana.ro",
    },
    "OT": {
        "dsvsa": "office-olt@ansvsa.ro",
        "politie": "cabinet@ot.politiaromana.ro",
    },
    "PH": {
        "dsvsa": "office-prahova@ansvsa.ro",
        "politie": "cabinet@ph.politiaromana.ro",
    },
    "SJ": {
        "dsvsa": "office-salaj@ansvsa.ro",
        "politie": "cabinet@sj.politiaromana.ro",
    },
    "SM": {
        "dsvsa": "office-satu-mare@ansvsa.ro",
        "politie": "cabinet@sm.politiaromana.ro",
    },
    "SB": {
        "dsvsa": "office-sibiu@ansvsa.ro",
        "politie": "cabinet@sb.politiaromana.ro",
    },
    "SV": {
        "dsvsa": "office-suceava@ansvsa.ro",
        "politie": "cabinet@sv.politiaromana.ro",
    },
    "TR": {
        "dsvsa": "office-teleorman@ansvsa.ro",
        "politie": "cabinet@tr.politiaromana.ro",
    },
    "TM": {
        "dsvsa": "office-timis@ansvsa.ro",
        "politie": "cabinet@tm.politiaromana.ro",
    },
    "TL": {
        "dsvsa": "office-tulcea@ansvsa.ro",
        "politie": "cabinet@tl.politiaromana.ro",
    },
    "VL": {
        "dsvsa": "office-valcea@ansvsa.ro",
        "politie": "cabinet@vl.politiaromana.ro",
    },
    "VS": {
        "dsvsa": "office-vaslui@ansvsa.ro",
        "politie": "cabinet@vs.politiaromana.ro",
    },
    "VN": {
        "dsvsa": "office-vrancea@ansvsa.ro",
        "politie": "cabinet@vn.politiaromana.ro",
    },
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
                    "attention_line": (
                        f"Către Biroul pentru Protecția Animalelor — județul {row.name}"
                    ),
                }
            )
        elif politie:
            recipients.append(
                {
                    "email": politie,
                    "label": "Poliția județeană (IPJ — BPA)",
                    "attention_line": (
                        f"Către Biroul pentru Protecția Animalelor — "
                        f"Inspectoratul de Poliție Județean {row.name}"
                    ),
                }
            )
        else:
            recipients.append(
                {
                    "email": "",
                    "label": "Poliția Animalelor / Poliție județeană",
                    "attention_line": (
                        f"Către Biroul pentru Protecția Animalelor — județul {row.name}"
                    ),
                    "pending": True,
                }
            )

    return recipients
