"""
Exportă unități veterinare CMVRO (https://cmvro.cmvro.ro/) în câte un CSV per județ,
cu antetul din Add USER — prospecte (staff_onboarding_csv.CSV_HEADER_ROW).

Exemplu:
  python manage.py cmvro_export_prospecte_judete --out "C:\\Users\\USER\\Desktop\\CMVRO_prospecte_judete"

Doar un județ:
  python manage.py cmvro_export_prospecte_judete --out "%USERPROFILE%\\Desktop\\CMVRO_prospecte_judete" --jude AB

Necesită internet; exportul național durează mult.
"""

from __future__ import annotations

import csv
import re
import time
import urllib.parse
import urllib.request
from pathlib import Path

from django.core.management.base import BaseCommand

from home.staff_onboarding_csv import CSV_HEADER_ROW

JUDETE = (
    "AB", "AG", "AR", "BC", "BH", "BN", "BT", "BV", "BR", "BZ", "CS", "CL", "CJ", "CT", "CV",
    "DB", "DJ", "GL", "GR", "GJ", "HR", "HD", "IL", "IS", "IF", "MM", "MH", "MS", "NT", "OT",
    "PH", "SM", "SJ", "SB", "SV", "TR", "TM", "TL", "VS", "VL", "VN", "B",
)

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/122.0.0.0 Safari/537.36 EU-Adopt-CMVRO-export/1.0"
BASE = "https://cmvro.cmvro.ro/cmvro/Unitati.aspx"

SUFFIXES = (
    "txtNumeUnitate",
    "txtJudet",
    "txtFormaOrganizare",
    "txtFormaActivitate",
    "txtNrCertificatInreg",
    "txtDataCertificatInreg",
    "txtTitularNume",
    "txtTitularPrenume",
    "txtTitularAtestatNr",
    "txtSSAdresa",
    "txtSSLocalitate",
    "txtSSJudet",
    "txtSSTelFix",
    "txtSSTelMob",
    "txtPLAdresa",
    "txtPLLocalitate",
    "txtPLJudet",
    "txtPLTelFix",
    "txtPLTelMob",
)
KEYS = (
    "nume_unitate",
    "judet_nume_cmvro",
    "forma_organizare",
    "forma_activitate",
    "nr_certificat_inreg",
    "data_certificat_inreg",
    "titular_nume",
    "titular_prenume",
    "titular_atestat_nr",
    "sediu_social_adresa",
    "sediu_social_localitate",
    "sediu_social_judet",
    "sediu_tel_fix",
    "sediu_tel_mobil",
    "pl_adresa",
    "pl_localitate",
    "pl_judet",
    "pl_tel_fix",
    "pl_tel_mobil",
)


def _phones(*parts: str) -> str:
    seen: set[str] = set()
    xs: list[str] = []
    for p in parts:
        t = (p or "").strip()
        if not t or t in ("-", "\u2013"):
            continue
        key = re.sub(r"\D+", "", t)
        if key in seen:
            continue
        seen.add(key or t)
        xs.append(t)
    return " / ".join(xs)


def _is_firma(r: dict[str, str]) -> bool:
    org = (r.get("nume_unitate") or "").lower()
    fo = (r.get("forma_organizare") or "").lower()
    fa = (r.get("forma_activitate") or "").lower()
    if "societate comercial" in fo or " - sc" in fa:
        return True
    if " srl" in org or org.endswith("srl") or " s.a." in org or org.endswith(" sa") or " sa " in org:
        return True
    return False


def _fetch_list_and_details(jud: str, stdout, delay_row: float, delay_between: float) -> list[dict[str, str]]:
    url = f"{BASE}?jud={urllib.parse.quote(jud)}"
    opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor())

    def get_page() -> str:
        req = urllib.request.Request(url, method="GET")
        req.add_header("User-Agent", UA)
        with opener.open(req, timeout=120) as resp:
            return resp.read().decode("utf-8", "replace")

    def post_page(data: bytes) -> str:
        req = urllib.request.Request(url, data=data, method="POST")
        req.add_header("User-Agent", UA)
        req.add_header("Content-Type", "application/x-www-form-urlencoded; charset=UTF-8")
        req.add_header("Referer", url)
        req.add_header("Origin", "https://cmvro.cmvro.ro")
        with opener.open(req, timeout=120) as resp:
            return resp.read().decode("utf-8", "replace")

    def all_hidden_inputs(html: str) -> dict[str, str]:
        fields: dict[str, str] = {}
        for m in re.finditer(r"<input[^>]+type=\"hidden\"[^>]*>", html, re.I):
            tag = m.group(0)
            nm = re.search(r'name="([^"]+)"', tag, re.I)
            if not nm:
                continue
            vm = re.search(r'value="([^"]*)"', tag, re.I)
            fields[nm.group(1)] = vm.group(1) if vm else ""
        return fields

    def extract_field2(html: str, suffix: str) -> str:
        pat = r'id="ctl00_ContentPlaceHolder1_' + re.escape(suffix) + r'"[^>]*class="field2"[^>]*>([^<]*)</span>'
        m = re.search(pat, html, re.I)
        return m.group(1).strip() if m else ""

    try:
        html0 = get_page()
    except Exception as e:
        stdout.write(stdout.style.WARNING(f"  [{jud}] listă: {e}\n"))
        return []

    pairs = re.findall(r"__doPostBack\('([^']+)','(Edit\$\d+)'\)", html0)
    if not pairs:
        stdout.write(f"  [{jud}] 0 rânduri (fără Edit$ în pagină).\n")
        return []

    out: list[dict[str, str]] = []
    for i, (target, arg) in enumerate(pairs):
        try:
            html_list = get_page()
            fields = all_hidden_inputs(html_list)
            body = dict(fields)
            body["__EVENTTARGET"] = target
            body["__EVENTARGUMENT"] = arg
            enc = urllib.parse.urlencode(body).encode()
            h = post_page(enc)
        except Exception as e:
            stdout.write(stdout.style.WARNING(f"  [{jud}] rând {i + 1}/{len(pairs)}: {e}\n"))
            time.sleep(delay_between)
            continue

        rec: dict[str, str] = {"judet_cod": jud}
        for key, suf in zip(KEYS, SUFFIXES, strict=True):
            rec[key] = extract_field2(h, suf)
        out.append(rec)
        time.sleep(delay_row)
        if delay_between and (i + 1) % 40 == 0:
            time.sleep(delay_between)

    return out


def _rows_to_prospect_csv(raw_rows: list[dict[str, str]], jud: str) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for r in raw_rows:
        tel = _phones(
            r.get("sediu_tel_mobil"),
            r.get("sediu_tel_fix"),
            r.get("pl_tel_mobil"),
            r.get("pl_tel_fix"),
        )
        firma = _is_firma(r)
        tip_cont = "colaborator"
        org = (r.get("nume_unitate") or "").strip()
        jud_nume = (r.get("sediu_social_judet") or r.get("judet_nume_cmvro") or "").strip()
        loc = (r.get("sediu_social_localitate") or "").strip()
        addr = (r.get("sediu_social_adresa") or "").strip()
        rep = ((r.get("titular_nume") or "") + " " + (r.get("titular_prenume") or "")).strip()
        note = (
            f"Cod județ sursă: {jud} | CMVRO {BASE}?jud={jud} | cert "
            + (r.get("nr_certificat_inreg") or "")
            + " din "
            + (r.get("data_certificat_inreg") or "")
            + " | "
            + (r.get("forma_organizare") or "")[:160]
        )
        if (r.get("pl_adresa") or "").strip():
            note += (
                " | PL: "
                + r["pl_adresa"].strip()
                + ", "
                + (r.get("pl_localitate") or "")
                + ", "
                + (r.get("pl_judet") or "")
            )
        rows.append(
            {
                "email": "",
                "telefon": tel,
                "tip_cont": tip_cont,
                "tip_colaborator": "CV",
                "prenume": r.get("titular_prenume") or "",
                "nume": r.get("titular_nume") or "",
                "denumire_afisata_contact": org,
                "username_propus": "",
                "judet": jud_nume,
                "localitate": loc,
                "denumire_organizatie": org if firma else "",
                "denumire_legala": org if firma else "",
                "cui": "",
                "cui_cu_ro": "",
                "reg_com": "",
                "adresa_firma": addr,
                "reprezentant_legal": rep if firma else "",
                "judet_firma": jud_nume if firma else "",
                "localitate_firma": loc if firma else "",
                "adapost_public_ong": "",
                "segmente": "noutati_colaboratori_servicii",
                "marketing_email_viitor": "",
                "nota_interna": note[:2000],
                "stare": "ready",
            }
        )
    return rows


class Command(BaseCommand):
    help = "Export CMVRO → CSV per județ (format prospecte Add USER)."

    def add_arguments(self, parser):
        parser.add_argument(
            "--out",
            default="",
            help="Folder destinație (ex. C:\\Users\\USER\\Desktop\\CMVRO_prospecte_judete). Obligatoriu.",
        )
        parser.add_argument(
            "--jude",
            default="",
            help="Dacă e setat, exportă doar acest cod (ex. AB). Altfel toate județele din listă.",
        )
        parser.add_argument(
            "--delay-row",
            type=float,
            default=0.25,
            help="Pauză secunde după fiecare unitate (default 0.25).",
        )
        parser.add_argument(
            "--delay-judet",
            type=float,
            default=1.5,
            help="Pauză suplimentară la fiecare ~40 unități și după fiecare județ (default 1.5).",
        )

    def handle(self, *args, **options):
        out_dir = (options.get("out") or "").strip()
        if not out_dir:
            self.stderr.write(self.style.ERROR("Lipsește --out (folder destinație).\n"))
            return
        path = Path(out_dir).expanduser()
        path.mkdir(parents=True, exist_ok=True)
        self.stdout.write(self.style.SUCCESS(f"Folder: {path}\n"))

        only = (options.get("jude") or "").strip().upper()
        codes = [only] if only else list(JUDETE)
        if only and only not in JUDETE:
            self.stderr.write(self.style.WARNING(f"Codul {only!r} nu e în lista standard; încerc oricum.\n"))

        delay_row = float(options["delay_row"])
        delay_j = float(options["delay_judet"])

        total_files = 0
        total_rows = 0
        for jud in codes:
            self.stdout.write(f"=== {jud} ===\n")
            raw = _fetch_list_and_details(jud, self.stdout, delay_row, delay_j)
            prospect_rows = _rows_to_prospect_csv(raw, jud)
            fn = path / f"prospecte_{jud}.csv"
            with fn.open("w", encoding="utf-8-sig", newline="") as f:
                w = csv.DictWriter(f, fieldnames=CSV_HEADER_ROW, extrasaction="ignore")
                w.writeheader()
                for row in prospect_rows:
                    w.writerow(row)
            self.stdout.write(self.style.SUCCESS(f"  scris: {fn.name} ({len(prospect_rows)} rânduri)\n"))
            total_files += 1
            total_rows += len(prospect_rows)
            time.sleep(delay_j)

        self.stdout.write(
            self.style.SUCCESS(f"Gata: {total_files} fișiere, {total_rows} rânduri total.\n")
        )
