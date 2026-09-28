"""Extrage listele de primării din răspunsul unui consiliu județean și le pune în coada de invitații.

Valul programat (9, 11, 13, 15) trimite mailul cu recomandarea și, dacă a venit, scrisoarea atașată.
Nu trimite în afara valului. Nu scrie din nou o adresă deja înregistrată.
"""
from __future__ import annotations

import csv
import io
import json
import logging
import re
import subprocess
import tempfile
import zipfile
from email.message import Message
from pathlib import Path
from xml.etree import ElementTree as ET

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.core.validators import validate_email
from django.db import transaction
from django.utils import timezone

from home.models import StaffOnboardingLead
from home.ro_location import normalize_lead_location_kwargs

logger = logging.getLogger(__name__)

_W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
_MIN_ROWS = 15
_LIST_EXT = {".doc", ".docx", ".xls", ".xlsx"}

_JUDETE: dict[str, tuple[str, str]] = {
    "alba": ("Alba", "AB"),
    "arad": ("Arad", "AR"),
    "arges": ("Argeș", "AG"),
    "bacau": ("Bacău", "BC"),
    "bihor": ("Bihor", "BH"),
    "bistrita-nasaud": ("Bistrița-Năsăud", "BN"),
    "botosani": ("Botoșani", "BT"),
    "braila": ("Brăila", "BR"),
    "brasov": ("Brașov", "BV"),
    "buzau": ("Buzău", "BZ"),
    "calarasi": ("Călărași", "CL"),
    "caras-severin": ("Caraș-Severin", "CS"),
    "cluj": ("Cluj", "CJ"),
    "constanta": ("Constanța", "CT"),
    "covasna": ("Covasna", "CV"),
    "dambovita": ("Dâmbovița", "DB"),
    "dolj": ("Dolj", "DJ"),
    "galati": ("Galați", "GL"),
    "giurgiu": ("Giurgiu", "GR"),
    "gorj": ("Gorj", "GJ"),
    "harghita": ("Harghita", "HR"),
    "hunedoara": ("Hunedoara", "HD"),
    "ialomita": ("Ialomița", "IL"),
    "iasi": ("Iași", "IS"),
    "ilfov": ("Ilfov", "IF"),
    "maramures": ("Maramureș", "MM"),
    "mehedinti": ("Mehedinți", "MH"),
    "mures": ("Mureș", "MS"),
    "neamt": ("Neamț", "NT"),
    "olt": ("Olt", "OT"),
    "prahova": ("Prahova", "PH"),
    "salaj": ("Sălaj", "SJ"),
    "satu mare": ("Satu Mare", "SM"),
    "sibiu": ("Sibiu", "SB"),
    "suceava": ("Suceava", "SV"),
    "teleorman": ("Teleorman", "TR"),
    "timis": ("Timiș", "TM"),
    "tulcea": ("Tulcea", "TL"),
    "valcea": ("Vâlcea", "VL"),
    "vaslui": ("Vaslui", "VS"),
    "vrancea": ("Vrancea", "VN"),
}

_EMAIL_RE = re.compile(r"[A-Z0-9._%+\-]+@[A-Z0-9.\-]+\.[A-Z]{2,}", re.I)
_PHONE_RE = re.compile(r"0\d{3}/\d{5,7}|07\d{8}")
_HEADER_RE = re.compile(
    r"^(?:\d+\.\s*)?(Județul|Municipiul|Orașul|Oraşul|Comuna)(?:\s+(.*))?$",
    re.I,
)
_SKIP_LINE = ("nr. crt", "unitatea", "datele de contact", "administrativ", "telefon", "e-mail")


def _fold_diacritics(text: str) -> str:
    return (
        (text or "")
        .replace("ş", "ș")
        .replace("Ş", "Ș")
        .replace("ţ", "ț")
        .replace("Ţ", "Ț")
    )


def _ascii(text: str) -> str:
    folded = _fold_diacritics(text).lower()
    folded = (
        folded.replace("ă", "a")
        .replace("â", "a")
        .replace("î", "i")
        .replace("ș", "s")
        .replace("ț", "t")
    )
    return re.sub(r"[^a-z0-9\- ]+", " ", folded)


def _lots_dir() -> Path:
    base = Path(getattr(settings, "BASE_DIR", ".") or ".")
    path = base / "static" / "staff_invite" / "cj_lots"
    path.mkdir(parents=True, exist_ok=True)
    return path


def _manifest_path() -> Path:
    return _lots_dir() / "manifest.json"


def _read_manifest() -> dict:
    path = _manifest_path()
    if not path.is_file():
        return {"lots": [], "seen_message_ids": []}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        logger.exception("cj_lista manifest ilizibil")
        return {"lots": [], "seen_message_ids": []}
    data.setdefault("lots", [])
    data.setdefault("seen_message_ids", [])
    return data


def _write_manifest(data: dict) -> None:
    path = _manifest_path()
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def detect_judet(text: str) -> tuple[str, str] | None:
    ascii_text = _ascii(text[:6000])
    match = re.search(r"judetul\s+([a-z][a-z\- ]{2,40})", ascii_text)
    if not match:
        match = re.search(r"consiliul judetean\s+([a-z][a-z\- ]{2,40})", ascii_text)
    if not match:
        return None
    chunk = re.sub(r"\s+", " ", match.group(1)).strip()
    for key in sorted(_JUDETE, key=len, reverse=True):
        if chunk.startswith(key):
            return _JUDETE[key]
    return None


def _clean_text(raw: str) -> str:
    text = (raw or "").replace("\xa0", " ")
    text = re.sub(r'HYPERLINK\s+"[^"]*"\s*(?:\\t\s+"[^"]*")?', "", text)
    return text


def parse_uat_contact_text(raw: str) -> list[dict]:
    text = _clean_text(raw)
    rows = _parse_headed_lines(text)
    if len([r for r in rows if r["emails"] and not r["kind"].lower().startswith("jude")]) < _MIN_ROWS:
        table_rows = _parse_delimited_table(text)
        if len(table_rows) > len(rows):
            rows = table_rows
    return rows


def _parse_headed_lines(text: str) -> list[dict]:
    lines = [re.sub(r"[ \t]+", " ", ln).strip() for ln in text.splitlines()]
    lines = [ln for ln in lines if ln]
    rows: list[dict] = []
    cur: dict | None = None

    def flush() -> None:
        nonlocal cur
        if not cur:
            return
        emails: list[str] = []
        for item in cur["emails"]:
            addr = item.lower().strip(".,;)")
            if addr and addr not in emails:
                emails.append(addr)
        phones: list[str] = []
        for item in cur["phones"]:
            if item not in phones:
                phones.append(item)
        rows.append(
            {
                "kind": _fold_diacritics(cur["kind"]),
                "name": _fold_diacritics(re.sub(r"\s+", " ", cur["name"]).strip(" .")),
                "phone": phones[0] if phones else "",
                "emails": emails,
            }
        )
        cur = None

    for ln in lines:
        low = ln.lower()
        if low.startswith(_SKIP_LINE) or low in {"telefon", "e-mail"}:
            continue
        match = _HEADER_RE.match(ln)
        if match:
            flush()
            rest = (match.group(2) or "").strip()
            cur = {"kind": match.group(1), "name": "", "phones": [], "emails": []}
            if rest:
                cur["emails"].extend(_EMAIL_RE.findall(rest))
                cur["phones"].extend(_PHONE_RE.findall(rest))
                cur["name"] = _PHONE_RE.sub("", _EMAIL_RE.sub("", rest)).strip(" .-\t")
            continue
        if cur is None:
            continue
        found_e = _EMAIL_RE.findall(ln)
        found_p = _PHONE_RE.findall(ln)
        if not cur["name"] and not found_e and not found_p:
            cur["name"] = ln.strip(" .")
            continue
        cur["emails"].extend(found_e)
        cur["phones"].extend(found_p)
    flush()
    return rows


def _parse_delimited_table(text: str) -> list[dict]:
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    header_idx = None
    delim = ","
    for i, ln in enumerate(lines[:40]):
        key = _ascii(ln)
        if "mail" not in key:
            continue
        if not any(token in key for token in ("uat", "unitat", "localit", "comuna", "primar", "denum")):
            continue
        if ln.count("\t") >= 2:
            delim = "\t"
        elif ln.count(";") >= 2:
            delim = ";"
        else:
            delim = ","
        header_idx = i
        break
    if header_idx is None:
        return []
    parsed = list(csv.reader(lines[header_idx:], delimiter=delim))
    if not parsed:
        return []
    header = [_ascii(cell) for cell in parsed[0]]

    def col(*needles: str) -> int | None:
        for idx, cell in enumerate(header):
            if any(needle in cell for needle in needles):
                return idx
        return None

    i_name = col("unitat", "localit", "uat", "comuna", "denum", "primar")
    i_mail = col("e-mail", "email", "mail")
    i_phone = col("telefon", "phone")
    if i_name is None or i_mail is None:
        return []
    rows = []
    for cells in parsed[1:]:
        if i_mail >= len(cells):
            continue
        emails = []
        for addr in _EMAIL_RE.findall(cells[i_mail]):
            low = addr.lower().strip(".,;)")
            if low not in emails:
                emails.append(low)
        if not emails:
            continue
        raw_name = cells[i_name].strip() if i_name < len(cells) else ""
        kind, name = _split_kind(raw_name)
        phone = ""
        if i_phone is not None and i_phone < len(cells):
            found = _PHONE_RE.findall(cells[i_phone])
            phone = found[0] if found else ""
        rows.append({"kind": kind, "name": _fold_diacritics(name), "phone": phone, "emails": emails})
    return rows


def _split_kind(raw_name: str) -> tuple[str, str]:
    match = _HEADER_RE.match(raw_name.strip())
    if match:
        return _fold_diacritics(match.group(1)), _fold_diacritics((match.group(2) or "").strip(" ."))
    return "Comuna", _fold_diacritics(raw_name.strip(" ."))


def _uat_category(kind: str) -> str:
    key = _ascii(kind)
    if key.startswith("municipi"):
        return StaffOnboardingLead.UAT_MUNICIPIU
    if key.startswith("oras"):
        return StaffOnboardingLead.UAT_ORAS
    return StaffOnboardingLead.UAT_COMUNA


def _usable_rows(rows: list[dict]) -> list[dict]:
    out = []
    for row in rows:
        if _ascii(row.get("kind") or "").startswith("judet"):
            continue
        name = (row.get("name") or "").strip()
        emails = [e for e in row.get("emails") or [] if _email_ok(e)]
        if not name or not emails:
            continue
        out.append({**row, "emails": emails})
    return out


def _email_ok(addr: str) -> bool:
    low = (addr or "").strip().lower()
    if not low or low.endswith("@eu-adopt.ro") or low.endswith("@example.invalid"):
        return False
    try:
        validate_email(low)
    except ValidationError:
        return False
    return True


def _text_from_docx(payload: bytes) -> str:
    lines: list[str] = []
    with zipfile.ZipFile(io.BytesIO(payload)) as zf:
        xml = zf.read("word/document.xml")
    root = ET.fromstring(xml)
    body = root.find(f"{_W}body")
    if body is None:
        return ""
    for el in list(body):
        tag = el.tag.split("}")[-1]
        if tag == "p":
            lines.append("".join(node.text or "" for node in el.iter(f"{_W}t")))
        elif tag == "tbl":
            for tr in el.iter(f"{_W}tr"):
                cells = []
                for tc in tr.findall(f"{_W}tc"):
                    cells.append("".join(node.text or "" for node in tc.iter(f"{_W}t")))
                lines.append("\t".join(cells))
    return "\n".join(lines)


def _text_from_xlsx(payload: bytes) -> str:
    ns = {"m": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
    with zipfile.ZipFile(io.BytesIO(payload)) as zf:
        shared: list[str] = []
        if "xl/sharedStrings.xml" in zf.namelist():
            root = ET.fromstring(zf.read("xl/sharedStrings.xml"))
            for si in root.findall("m:si", ns):
                shared.append("".join(node.text or "" for node in si.iter(f"{{{ns['m']}}}t")))
        sheet_name = "xl/worksheets/sheet1.xml"
        if sheet_name not in zf.namelist():
            sheets = [n for n in zf.namelist() if n.startswith("xl/worksheets/sheet")]
            if not sheets:
                return ""
            sheet_name = sorted(sheets)[0]
        root = ET.fromstring(zf.read(sheet_name))
    lines = []
    for row in root.findall("m:sheetData/m:row", ns):
        cells = []
        for cell in row.findall("m:c", ns):
            kind = cell.attrib.get("t")
            value = cell.find("m:v", ns)
            text = ""
            if kind == "s" and value is not None and value.text and value.text.isdigit():
                idx = int(value.text)
                text = shared[idx] if idx < len(shared) else ""
            elif kind == "inlineStr":
                text = "".join(node.text or "" for node in cell.iter(f"{{{ns['m']}}}t"))
            elif value is not None and value.text:
                text = value.text
            cells.append(text)
        if any(cells):
            lines.append("\t".join(cells))
    return "\n".join(lines)


def _text_via_cmd(cmd: list[str], payload: bytes, suffix: str) -> str:
    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
        tmp.write(payload)
        path = tmp.name
    try:
        result = subprocess.run(cmd + [path], capture_output=True, timeout=60, check=False)
    except (OSError, subprocess.TimeoutExpired):
        logger.exception("cj_lista convert %s", cmd[0])
        return ""
    finally:
        Path(path).unlink(missing_ok=True)
    return result.stdout.decode("utf-8", errors="replace")


def text_from_attachment(name: str, payload: bytes) -> str:
    ext = Path(name or "").suffix.lower()
    if not payload or len(payload) > 15_000_000:
        return ""
    try:
        if ext == ".docx":
            return _text_from_docx(payload)
        if ext == ".xlsx":
            return _text_from_xlsx(payload)
        if ext == ".doc":
            return _text_via_cmd(["catdoc", "-d", "utf-8"], payload, ".doc")
        if ext == ".xls":
            return _text_via_cmd(["xls2csv", "-d", "utf-8"], payload, ".xls")
    except (OSError, KeyError, ET.ParseError, zipfile.BadZipFile):
        logger.exception("cj_lista atașament %s", ext)
    return ""


def _attachments(msg: Message) -> list[tuple[str, bytes]]:
    found = []
    if not msg.is_multipart():
        return found
    for part in msg.walk():
        name = part.get_filename()
        if not name:
            continue
        payload = part.get_payload(decode=True) or b""
        found.append((str(name), payload))
    return found


def _pick_pdf(attachments: list[tuple[str, bytes]]) -> tuple[str, bytes] | None:
    pdfs = [(n, p) for n, p in attachments if n.lower().endswith(".pdf") and p]
    if not pdfs:
        return None

    def rank(item: tuple[str, bytes]) -> tuple[int, int]:
        low = _ascii(item[0])
        preferred = 0 if any(token in low for token in ("adresa", "raspuns", "circular", "recomand")) else 1
        return (preferred, -len(item[1]))

    return sorted(pdfs, key=rank)[0]


def _owner():
    User = get_user_model()
    return (
        User.objects.filter(username__iexact="rares", is_staff=True).first()
        or User.objects.filter(is_superuser=True).first()
    )


def _marker_for(judet: str, code: str) -> str:
    from home.staff_onboarding_invite import _all_cj_lista_lots

    for marker, label, _dorese, _rel, _fname in _all_cj_lista_lots():
        if label.casefold() == judet.casefold():
            return marker
    yyyymm = timezone.localtime().strftime("%Y%m")
    return f"[SURSA:CJ{code}_LISTA_{yyyymm}]"


def _ensure_lot(marker: str, judet: str, pdf: tuple[str, bytes] | None) -> None:
    from home.staff_onboarding_invite import _CJ_LISTA_LOTS

    if any(lot[0] == marker for lot in _CJ_LISTA_LOTS):
        return
    data = _read_manifest()
    for lot in data["lots"]:
        if lot.get("marker") == marker:
            return
    pdf_rel = ""
    pdf_name = ""
    if pdf:
        safe = re.sub(r"[^A-Za-z0-9._-]+", "_", pdf[0]) or "adresa.pdf"
        if not safe.lower().endswith(".pdf"):
            safe += ".pdf"
        dest = _lots_dir() / f"{marker.strip('[]').replace(':', '_')}_{safe}"
        dest.write_bytes(pdf[1])
        pdf_rel = str(dest.relative_to(Path(getattr(settings, "BASE_DIR", ".") or "."))).replace("\\", "/")
        pdf_name = safe
    data["lots"].append(
        {
            "marker": marker,
            "judet": judet,
            "pdf_rel": pdf_rel,
            "pdf_name": pdf_name,
        }
    )
    _write_manifest(data)


def _remember_message(message_id: str) -> None:
    if not message_id:
        return
    data = _read_manifest()
    seen = data["seen_message_ids"]
    if message_id in seen:
        return
    seen.append(message_id)
    data["seen_message_ids"] = seen[-500:]
    _write_manifest(data)


def register_cj_rows(*, judet: str, code: str, rows: list[dict], pdf: tuple[str, bytes] | None) -> dict:
    usable = _usable_rows(rows)
    if len(usable) < _MIN_ROWS:
        return {"status": "short", "created": 0, "rows": len(usable)}
    marker = _marker_for(judet, code)
    _ensure_lot(marker, judet, pdf)
    owner = _owner()
    created = 0
    skipped = 0
    with transaction.atomic():
        for row in usable:
            cat = _uat_category(row["kind"])
            for addr in row["emails"]:
                if StaffOnboardingLead.objects.filter(email__iexact=addr).exists():
                    skipped += 1
                    continue
                payload = {
                    "email": addr,
                    "phone": (row.get("phone") or "")[:40],
                    "display_name": f"Primăria {row['name']}"[:200],
                    "org_display_name": f"Primăria {row['name']}"[:255],
                    "company_legal_name": f"Primăria {row['name']}"[:255],
                    "account_kind": StaffOnboardingLead.KIND_ADAPOST,
                    "collaborator_subtype": StaffOnboardingLead.COLLAB_ADPUB,
                    "is_public_shelter": True,
                    "uat_category": cat,
                    "judet": judet,
                    "oras": row["name"][:120],
                    "notes": f"{marker} Import automat listă CJ {judet}. Primăria {row['name']}",
                    "status": StaffOnboardingLead.ST_READY,
                    "invite_mail_status": StaffOnboardingLead.INVITE_NEVER,
                }
                payload = normalize_lead_location_kwargs(payload)
                StaffOnboardingLead.objects.create(created_by=owner, **payload)
                created += 1
    logger.info("cj_lista %s create=%s existente=%s", judet, created, skipped)
    return {"status": "imported", "created": created, "skipped": skipped, "judet": judet, "marker": marker}


def maybe_import_cj_lista_message(msg: Message) -> dict:
    """Din un mesaj IMAP. Returnează status skip | imported | short."""
    message_id = (msg.get("Message-ID") or "").strip()
    if message_id and message_id in set(_read_manifest().get("seen_message_ids") or []):
        return {"status": "skip", "created": 0}

    attachments = _attachments(msg)
    list_parts = [(n, p) for n, p in attachments if Path(n).suffix.lower() in _LIST_EXT]
    if not list_parts:
        return {"status": "skip", "created": 0}

    chunks = []
    for name, payload in list_parts:
        text = text_from_attachment(name, payload)
        if text.strip():
            chunks.append(text)
    combined = "\n".join(chunks)
    found = detect_judet(combined)
    rows = parse_uat_contact_text(combined) if combined else []
    usable = _usable_rows(rows)
    if not found or len(usable) < _MIN_ROWS:
        logger.info(
            "cj_lista nesigur from=%s atasamente=%s judet=%s randuri=%s",
            msg.get("From"),
            [n for n, _p in list_parts],
            found[0] if found else "",
            len(usable),
        )
        return {"status": "short", "created": 0, "rows": len(usable)}

    judet, code = found
    result = register_cj_rows(judet=judet, code=code, rows=rows, pdf=_pick_pdf(attachments))
    if result.get("status") == "imported":
        _remember_message(message_id)
    return result
