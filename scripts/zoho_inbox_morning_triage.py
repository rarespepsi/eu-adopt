#!/usr/bin/env python3
"""Morning Zoho INBOX triage: list + classify + move to EU_* folders. Report to stdout."""
import os
import sys
import re
import imaplib
import email
from email.header import decode_header

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "euadopt_final.settings")
sys.path.insert(0, "/opt/eu-adopt")
import django

django.setup()
from django.conf import settings

FOLDERS = [
    "EU_Media_Radio_TV",
    "EU_Primarii_CJ",
    "EU_Colaboratori",
    "EU_Utilizatori_Site",
    "EU_Bounce",
    "EU_Rapoarte_Intern",
]


def dec(s):
    if s is None:
        return ""
    if isinstance(s, bytes):
        parts = decode_header(s.decode("utf-8", "replace"))
    else:
        parts = decode_header(s)
    out = []
    for frag, enc in parts:
        if isinstance(frag, bytes):
            out.append(frag.decode(enc or "utf-8", "replace"))
        else:
            out.append(frag)
    return "".join(out)


def _from_domain(frm: str) -> str:
    """Extrage domeniul din From (după @, până la > sau spațiu)."""
    f = (frm or "").casefold()
    m = re.search(r"@([a-z0-9._-]+\.[a-z]{2,})", f)
    return (m.group(1) if m else "").rstrip(">")


def classify(frm: str, subj: str) -> str | None:
    f = (frm or "").casefold()
    s = (subj or "").casefold()
    blob = f"{f} {s}"
    domain = _from_domain(frm)

    if "mailer-daemon@" in f or "undelivered mail" in s or "delivery status" in s:
        return "EU_Bounce"

    # DMARC / rapoarte automate / alerte Zoho — fără răspuns uman
    if (
        "dmarc" in f
        or "dmarc" in s
        or "noreply-dmarc" in f
        or "dmarcreport@" in f
        or ("report domain:" in s and "eu-adopt" in s)
        or ("outgoing blocked" in s and "zoho" in blob)
        or ("noreply@zoho" in f and "blocked" in s)
    ):
        return "EU_Rapoarte_Intern"

    if "contact@eu-adopt.ro" in f and (
        "invitații" in s or "invitatii" in s or "[eu-adopt]" in s
    ):
        return "EU_Rapoarte_Intern"

    # Primării / CJ înainte de Media (evită „maria” în „primaria”)
    # Orice domeniu tipic CJ: cjarges.ro, cjvrancea.ro, cjsj.ro, cjvalcea.ro, cjolt.ro, …
    if domain.startswith("cj") and domain.endswith(".ro"):
        return "EU_Primarii_CJ"
    if re.search(r"@cj[a-z0-9-]*\.ro\b", f):
        return "EU_Primarii_CJ"

    prim_hints = (
        "primaria",
        "primăria",
        "primar",
        "consiliul județean",
        "consiliul judetean",
        "registratura",
        "aspa",
        "protectia animalelor",
        "protecția animalelor",
        "oradea.ro",
        "onesti.ro",
        "bragadiru",
        "mogosani",
        "platformă gratuită eu-adopt",
        "platforma gratuita eu-adopt",
        "invitație eu-adopt",
        "invitatie eu-adopt",
        "listă uat",
        "lista uat",
        "adrese de email primarii",
    )
    if any(h in blob for h in prim_hints):
        return "EU_Primarii_CJ"

    media_hints = (
        "radio ",
        "radio-",
        "kanal",
        "metronom",
        "playradio",
        "play radio",
        "radiosomes",
        "radio someș",
        "radio somes",
        "radiogaga",
        "radio gaga",
        "teculescu",
        "radiomaria",
        "radio maria",
        "star sebes",
        "star sebeș",
        "radioconstanta",
        "radio constanta",
        "radio constanța",
        "colaborare eu-adopt ×",
        "colaborare eu-adopt x",
        "difuzare spot",
        " kanal ",
        "@kanald",
    )
    if any(h in blob for h in media_hints) or "radio" in f:
        return "EU_Media_Radio_TV"

    collab_hints = (
        "paws-hope",
        "paws hope",
        "adpludus",
        "ludus",
        "magazin produse",
        "colaborare gratuită",
        "colaborare gratuita",
    )
    if any(h in blob for h in collab_hints):
        return "EU_Colaboratori"

    site_hints = ("serbacov", "campanii sterilizare", "nu apar campaniile")
    if any(h in blob for h in site_hints):
        return "EU_Utilizatori_Site"

    return None


def needs_reply(dest: str | None, frm: str, subj: str) -> str:
    """Returnează eticheta acțiune pentru raport."""
    f = (frm or "").casefold()
    s = (subj or "").casefold()
    if dest == "EU_Bounce":
        return "nu (bounce)"
    if dest == "EU_Rapoarte_Intern":
        return "nu (raport intern)"
    if dest == "EU_Media_Radio_TV":
        if s.startswith("re:") or s.startswith("re :"):
            return "DA — răspuns media / partener"
        return "verifică — media nouă"
    if dest == "EU_Primarii_CJ":
        if any(
            x in s
            for x in (
                "raspuns",
                "răspuns",
                "adresa",
                "confirm",
                "listă",
                "lista",
                "uat",
            )
        ) or s.startswith("re:"):
            return "DA — răspuns / confirmare primărie sau CJ"
        return "DA — răspuns primărie/CJ dacă e cerere"
    if dest == "EU_Colaboratori":
        return "DA — răspuns colaborator"
    if dest == "EU_Utilizatori_Site":
        return "DA — suport site"
    if "mailer-daemon@" in f:
        return "nu (bounce)"
    return "verifică manual"


def ensure_folder(M, name: str):
    typ, data = M.list()
    existing = set()
    for raw in data or []:
        line = raw.decode("utf-8", "replace") if isinstance(raw, bytes) else str(raw)
        m = re.findall(r'"([^"]*)"', line)
        if m:
            existing.add(m[-1])
        else:
            existing.add(line.split()[-1].strip())
    if name not in existing:
        M.create(name)


def move_uid(M, uid: bytes, dest: str) -> bool:
    typ, _ = M.uid("MOVE", uid, dest)
    if typ == "OK":
        return True
    typ, _ = M.uid("COPY", uid, dest)
    if typ != "OK":
        return False
    M.uid("STORE", uid, "+FLAGS", r"(\Deleted)")
    return True


host = (settings.STAFF_INVITE_IMAP_HOST or "").strip() or "imap.zoho.eu"
port = int(getattr(settings, "STAFF_INVITE_IMAP_PORT", 993) or 993)
user = (settings.STAFF_INVITE_IMAP_USER or "").strip()
pw = (settings.STAFF_INVITE_IMAP_PASSWORD or "").strip()
M = None
_last_err = None
for _attempt in range(1, 5):
    try:
        M = imaplib.IMAP4_SSL(host, port, timeout=90)
        M.login(user, pw)
        break
    except Exception as exc:
        _last_err = exc
        import time as _time

        _time.sleep(4 * _attempt)
if M is None:
    raise SystemExit(f"IMAP login failed: {_last_err}")
for name in FOLDERS:
    ensure_folder(M, name)

typ, _ = M.select("INBOX")
typ, data = M.uid("SEARCH", None, "ALL")
uids = (data[0] or b"").split()

print(f"## Raport INBOX Zoho ({len(uids)} mesaje)")
print("")

rows = []
moved = {k: 0 for k in FOLDERS}
kept = 0
errors = 0

for uid in uids:
    typ, msgdata = M.uid("FETCH", uid, "(BODY.PEEK[HEADER.FIELDS (FROM SUBJECT DATE)])")
    if typ != "OK" or not msgdata or not isinstance(msgdata[0], tuple):
        continue
    msg = email.message_from_bytes(msgdata[0][1])
    frm = dec(msg.get("From", ""))
    subj = dec(msg.get("Subject", ""))
    date_s = dec(msg.get("Date", ""))[:28]
    dest = classify(frm, subj)
    act = needs_reply(dest, frm, subj)
    rows.append((date_s, frm, subj, dest or "INBOX", act))
    if dest:
        if move_uid(M, uid, dest):
            moved[dest] += 1
        else:
            errors += 1
            kept += 1
    else:
        kept += 1

try:
    M.expunge()
except Exception:
    pass

if not rows:
    print("- Inbox gol. Nimic de raportat.")
else:
    print("| Data | De la | Subiect | Folder | Răspuns? |")
    print("|------|-------|---------|--------|----------|")
    for date_s, frm, subj, dest, act in rows:
        print(
            f"| {date_s.replace('|','/')} | {frm[:42].replace('|','/')} | {subj[:48].replace('|','/')} | {dest} | {act} |"
        )

print("")
print("### Mutări")
for k, v in moved.items():
    if v:
        print(f"- {k}: {v}")
print(f"- rămase în INBOX (neclasificate / erori): {kept}")
if errors:
    print(f"- erori mutare: {errors}")

# acțiuni prioritare
print("")
print("### Unde trebuie să răspunzi")
urgent = [r for r in rows if r[4].startswith("DA")]
if not urgent:
    print("- nimic urgent din acest batch")
else:
    for date_s, frm, subj, dest, act in urgent:
        print(f"- [{dest}] {frm[:40]} — {subj[:55]}")

M.logout()
print("")
print("DONE")
