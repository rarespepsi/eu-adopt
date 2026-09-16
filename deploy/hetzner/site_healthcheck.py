#!/usr/bin/env python3
"""
Site healthcheck: smoke HTTP + Maps source checks + SHA vs EXPECTED_RELEASE.
Exit 0 = OK, 1 = FAIL. Fără secrete în output.

Modes:
  check  — full (default, cron)
  smoke  — HTTP + Maps source only (post-deploy; fără SHA/dirty)
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

APP_DIR = Path(os.environ.get("EUADOPT_APP_DIR", "/opt/eu-adopt"))
EXPECTED_PATH = Path(
    os.environ.get("EUADOPT_EXPECTED_RELEASE", "/var/lib/euadopt/EXPECTED_RELEASE.txt")
)
BASE_URL = (os.environ.get("EUADOPT_HEALTHCHECK_BASE_URL") or "https://eu-adopt.ro").rstrip("/")

# Hub Eu + piețe TLD + Cazareamea — doar GET / (200, fără „Bad Request”).
# Override: EUADOPT_HEALTHCHECK_EXTRA_BASE_URLS=url1,url2
_DEFAULT_EXTRA_BASES = (
    "https://euadopt.com",
    "https://euadopt.de",
    "https://euadopt.fr",
    "https://euadopt.es",
    "https://cazareamea.ro",
)

# Host-uri EU: nu trebuie să servească app-ul Cazareamea (regresie nginx catch-all).
_EU_ADOPT_BASES = (
    "https://euadopt.com",
    "https://euadopt.de",
    "https://euadopt.fr",
    "https://euadopt.es",
)
_EU_HOME_MARKERS = ("page-home-v2", "hero-v2")
_CAZAREA_FORBIDDEN_ON_EU = ("cazareamea", "Cazarea Mea", "cazarea mea")
_EU_SERVER_NAMES_REQUIRED = (
    "euadopt.com",
    "euadopt.de",
    "euadopt.fr",
    "euadopt.es",
)
_NGINX_EU_ENABLED = Path(
    os.environ.get("EUADOPT_NGINX_EU_ENABLED", "/etc/nginx/sites-enabled/eu-adopt")
)
_NGINX_CAZAREA_ENABLED = Path(
    os.environ.get("EUADOPT_NGINX_CAZAREA_ENABLED", "/etc/nginx/sites-enabled/cazareamea")
)


def extra_base_urls() -> list[str]:
    raw = (os.environ.get("EUADOPT_HEALTHCHECK_EXTRA_BASE_URLS") or "").strip()
    if raw:
        return [u.strip().rstrip("/") for u in raw.split(",") if u.strip()]
    return list(_DEFAULT_EXTRA_BASES)


# path → needles (empty = doar HTTP 200). Contact: vezi run_smoke (prelaunch → login).
SMOKE_CHECKS: list[tuple[str, list[str]]] = [
    ("/", []),
    ("/pets/", []),
    ("/servicii/", []),
    ("/transport/", ["plecare_map_pick", "sosire_map_pick", "transportMapModal"]),
    ("/shop/", []),
    ("/contact/", []),  # special: 302→login OK în prelaunch; 200 → phone markers
    ("/signup/colaborator/", ["signup_col_map_pick", "signup_col_map_modal", "safeAutocomplete"]),
    ("/signup/organizatie/", ["signup_org_map_pick", "signup_org_map_modal"]),
    ("/login/", []),
    ("/termeni-si-conditii/", []),
    ("/i-love/", []),
]

CONTACT_PHONE_NEEDLES = ["wa.me/40733823678", "+40 73 EUADOPT", "WhatsApp"]

_FORBIDDEN_MIXED_TYPES = re.compile(
    r"types\s*:\s*\[\s*['\"]establishment['\"]\s*,\s*['\"]geocode['\"]\s*\]"
    r"|types\s*:\s*\[\s*['\"]geocode['\"]\s*,\s*['\"]establishment['\"]\s*\]",
    re.IGNORECASE,
)

# Dirty pe H ignorat: zgomot CRLF / fișiere pe care cron-ul le poate atinge fără schimbare de conținut.
_DIRTY_IGNORE_SUBSTRINGS = (
    "AUTO_REPAIR_STATE",
    ".pyc",
    "EXPECTED_RELEASE.txt",
)
_DIRTY_IGNORE_PATHS = frozenset(
    {
        "deploy/hetzner/install_cleanup_lost_found_cron.sh",
        "deploy/hetzner/run_cleanup_lost_found.sh",
    }
)


def _porcelain_path(line: str) -> str:
    """Extrage path din linie `git status --porcelain` (fără rename complex)."""
    s = (line or "").rstrip("\n")
    if len(s) < 4:
        return ""
    # XY<space>path  sau  XY path -> path
    rest = s[3:] if s[2:3] == " " else s[2:].lstrip()
    if " -> " in rest:
        rest = rest.split(" -> ", 1)[-1]
    return rest.strip().strip('"')


def _git_diff_has_content(cwd: Path, rel_path: str) -> bool:
    """False dacă diff-ul e gol (inclusiv doar CRLF / fără linii schimbate)."""
    if not rel_path:
        return True
    try:
        numstat = subprocess.check_output(
            ["git", "diff", "--numstat", "--", rel_path],
            cwd=str(cwd),
            text=True,
            stderr=subprocess.DEVNULL,
        ).strip()
        cached = subprocess.check_output(
            ["git", "diff", "--cached", "--numstat", "--", rel_path],
            cwd=str(cwd),
            text=True,
            stderr=subprocess.DEVNULL,
        ).strip()
    except Exception:
        return True
    combined = "\n".join(x for x in (numstat, cached) if x)
    if not combined:
        return False
    for row in combined.splitlines():
        parts = row.split("\t")
        if len(parts) < 2:
            continue
        a, b = parts[0], parts[1]
        if a == "-" and b == "-":  # binary touched
            return True
        try:
            if int(a) > 0 or int(b) > 0:
                return True
        except ValueError:
            return True
    return False


def meaningful_git_dirty_lines(cwd: Path, porcelain: str) -> list[str]:
    """Filtrează dirty irelevant (EXPECTED, CRLF-only, scripturi cleanup cunoscute)."""
    out: list[str] = []
    for ln in (porcelain or "").splitlines():
        if not ln.strip() or ln.startswith("??"):
            continue
        if any(s in ln for s in _DIRTY_IGNORE_SUBSTRINGS):
            continue
        path = _porcelain_path(ln)
        if path in _DIRTY_IGNORE_PATHS:
            continue
        if path.startswith("deploy/hetzner/") and path.endswith(".sh"):
            # Scripturi shell pe H: dacă nu e schimbare de conținut → ignoră (CRLF).
            if not _git_diff_has_content(cwd, path):
                continue
        elif not _git_diff_has_content(cwd, path):
            continue
        out.append(ln)
    return out


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def parse_expected(path: Path) -> dict[str, str]:
    out: dict[str, str] = {}
    if not path.is_file():
        return out
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        s = line.strip()
        if not s or s.startswith("#") or "=" not in s:
            continue
        k, v = s.split("=", 1)
        out[k.strip()] = v.strip()
    return out


def sha_match(live: str, expected: str) -> bool:
    live = (live or "").strip().lower()
    expected = (expected or "").strip().lower()
    if not live or not expected:
        return False
    return live == expected or live.startswith(expected) or expected.startswith(live)


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):  # noqa: ANN001
        return None


def http_get_url(url: str, timeout: int = 25, follow: bool = True) -> tuple[int, str, Optional[str]]:
    """Return (status, body, location_header_if_redirect)."""
    req = urllib.request.Request(
        url,
        headers={"User-Agent": "EUAdopt-Healthcheck/1.0"},
        method="GET",
    )
    opener = urllib.request.build_opener() if follow else urllib.request.build_opener(_NoRedirect)
    try:
        with opener.open(req, timeout=timeout) as resp:
            body = resp.read().decode("utf-8", errors="replace")
            return int(resp.status), body, None
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace") if e.fp else ""
        loc = e.headers.get("Location") if e.headers else None
        return int(e.code), body, loc
    except Exception as e:
        return 0, f"{type(e).__name__}: {e}", None


def http_get(path: str, timeout: int = 25, follow: bool = True) -> tuple[int, str, Optional[str]]:
    return http_get_url(BASE_URL + path, timeout=timeout, follow=follow)


def run_smoke() -> list[str]:
    fails: list[str] = []
    for path, needles in SMOKE_CHECKS:
        if path == "/contact/":
            code, body, loc = http_get(path, follow=False)
            if code in (301, 302, 303, 307, 308) and loc and "/login/" in loc:
                continue  # prelaunch / auth gate — OK
            if code == 200:
                if not any(n in body for n in CONTACT_PHONE_NEEDLES):
                    fails.append(f"missing contact phone/whatsapp markers on {path}")
                continue
            fails.append(f"HTTP {code} {path} loc={loc} :: {str(body)[:120]}")
            continue

        code, body, _ = http_get(path, follow=True)
        if code != 200:
            fails.append(f"HTTP {code} {path} :: {str(body)[:180]}")
            continue
        if not needles:
            continue
        missing = [n for n in needles if n not in body]
        if not missing:
            continue
        map_only = all(
            ("map" in m.lower()) or ("Modal" in m) or (m == "safeAutocomplete") for m in missing
        )
        if map_only and "maps.googleapis.com" not in body:
            continue
        fails.append(f"missing {missing} on {path}")
    return fails


def run_extra_sites_check() -> list[str]:
    """
    Smoke minim pe hub Eu (.com/.de/.fr/.es) + Cazareamea.
    Prinde regresii tip nginx catch-all greșit (400 Bad Request pe host)
    și rutare EU → Cazareamea (pagină greșită cu 200).
    """
    fails: list[str] = []
    eu_set = {u.rstrip("/") for u in _EU_ADOPT_BASES}
    for base in extra_base_urls():
        base_n = base.rstrip("/")
        code, body, loc = http_get_url(base_n + "/", follow=True)
        if code in (301, 302) and loc:
            # un redirect HTTPS/apex e OK dacă destinația tot pe același host-ish
            code2, body2, _ = http_get_url(loc if loc.startswith("http") else base_n + loc, follow=True)
            code, body = code2, body2
        low = (body or "").lower()
        if code != 200:
            fails.append(f"extra_site HTTP {code} {base_n}/ :: {str(body)[:120]}")
            continue
        if "bad request" in low and "<h1>bad request" in low:
            fails.append(f"extra_site Bad Request page on {base_n}/")
            continue
        if base_n in eu_set:
            for bad in _CAZAREA_FORBIDDEN_ON_EU:
                if bad.lower() in low:
                    fails.append(
                        f"extra_site EU host served Cazareamea content on {base_n}/ "
                        f"(marker={bad!r}) — check nginx default_server / server_name"
                    )
                    break
            missing = [m for m in _EU_HOME_MARKERS if m not in (body or "")]
            if missing:
                fails.append(
                    f"extra_site EU home missing {missing} on {base_n}/ "
                    "(not EU-Adopt app?)"
                )
    return fails


def run_nginx_eu_vhost_guard() -> list[str]:
    """
    Guard pe Hetzner: eu-adopt e default_server SSL, symlink enabled→available,
    domeniile EU sunt în server_name, cazareamea nu e default_server.
    Skip graceful dacă /etc/nginx nu e citibil (ex. check local fără nginx).
    """
    fails: list[str] = []
    if not _NGINX_EU_ENABLED.exists() and not Path("/etc/nginx/sites-available/eu-adopt").exists():
        # Mediu fără nginx local (dev PC) — nu eșuează deploy-ul de pe laptop
        return []
    try:
        eu_path = _NGINX_EU_ENABLED
        if not eu_path.exists():
            fails.append("nginx_vhost: sites-enabled/eu-adopt missing")
            return fails
        if not eu_path.is_symlink():
            fails.append(
                "nginx_vhost: sites-enabled/eu-adopt is not a symlink "
                "(copie separată → riscul regresiei catch-all); "
                "rulează deploy/hetzner/repair_eu_nginx_catchall.sh"
            )
        eu_text = eu_path.read_text(encoding="utf-8", errors="replace")
    except OSError as e:
        fails.append(f"nginx_vhost: cannot read eu-adopt config: {e}")
        return fails

    if "default_server" not in eu_text:
        fails.append(
            "nginx_vhost: eu-adopt has no default_server on SSL — "
            "unknown Host may fall through to another vhost (ex. cazareamea)"
        )
    for name in _EU_SERVER_NAMES_REQUIRED:
        if name not in eu_text:
            fails.append(f"nginx_vhost: server_name missing {name} in eu-adopt")

    if _NGINX_CAZAREA_ENABLED.exists():
        try:
            caz_text = _NGINX_CAZAREA_ENABLED.read_text(encoding="utf-8", errors="replace")
        except OSError as e:
            fails.append(f"nginx_vhost: cannot read cazareamea config: {e}")
            return fails
        # default_server pe cazareamea = regresia clasică
        if re.search(r"listen\s+[^\n;]*443[^\n;]*default_server", caz_text):
            fails.append(
                "nginx_vhost: cazareamea is SSL default_server — "
                "EU unknown/mis-matched Host can route to :8001; "
                "rulează deploy/hetzner/repair_eu_nginx_catchall.sh"
            )
        if "euadopt.com" in caz_text or "eu-adopt.ro" in caz_text:
            fails.append("nginx_vhost: cazareamea server_name unexpectedly lists EU-Adopt hosts")
    return fails


def run_phone_source_check() -> list[str]:
    """Telefon public — verifică sursa (paginile pot fi în spatele login prelaunch)."""
    fails: list[str] = []
    py = APP_DIR / "home" / "euadopt_public_contact.py"
    if not py.is_file():
        return [f"missing {py}"]
    src = py.read_text(encoding="utf-8", errors="replace")
    for needle in ("+40733823678", "+40 73 EUADOPT", "wa.me/", "40733823678"):
        if needle not in src:
            fails.append(f"phone_source missing {needle} in {py.name}")
    return fails


def run_maps_source_check() -> list[str]:
    """
    Verifică sursa Maps fără create-database (euadopt nu are CREATEDB pe Postgres).
    Acoperă aceleași regresii ca GoogleMapsPickerSourceTests.
    """
    fails: list[str] = []
    signup = APP_DIR / "templates" / "anunturi" / "includes" / "signup_adresa_google_maps_script.html"
    transport = APP_DIR / "templates" / "anunturi" / "transport.html"
    for path, must in (
        (
            signup,
            ("safeAutocomplete", "document.body.appendChild(mapModal)", "componentRestrictions"),
        ),
        (
            transport,
            ("safeAutocomplete", "document.body.appendChild(transportMapModal)"),
        ),
    ):
        if not path.is_file():
            fails.append(f"maps_source missing file {path}")
            continue
        src = path.read_text(encoding="utf-8", errors="replace")
        if _FORBIDDEN_MIXED_TYPES.search(src):
            fails.append(f"maps_source forbidden mixed Places types in {path.name}")
        for m in must:
            if m not in src:
                fails.append(f"maps_source missing {m!r} in {path.name}")
    return fails


def main() -> int:
    mode = (sys.argv[1] if len(sys.argv) > 1 else "check").strip().lower()
    report: list[str] = [f"time={_now()}", f"base_url={BASE_URL}", f"mode={mode}"]
    expected = parse_expected(EXPECTED_PATH)
    exp_sha = (expected.get("SHA") or "").strip()
    report.append(f"expected_sha={exp_sha or '(missing)'}")
    report.append(f"expected_file={EXPECTED_PATH}")

    fails: list[str] = []

    try:
        live = subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=str(APP_DIR), text=True
        ).strip()
    except Exception as e:
        live = ""
        fails.append(f"git_rev_parse: {e}")
    report.append(f"live_sha={live or '(unknown)'}")

    if mode != "smoke":
        if not exp_sha:
            fails.append("expected_release_missing")
        elif live and not sha_match(live, exp_sha):
            fails.append(f"sha_mismatch live={live} expected={exp_sha}")

        try:
            # Doar fișiere tracked modificate (untracked pe H e normal: exports, tmp, venv)
            dirty = subprocess.check_output(
                ["git", "status", "--porcelain", "-uno"], cwd=str(APP_DIR), text=True
            ).strip()
            if dirty:
                lines = meaningful_git_dirty_lines(APP_DIR, dirty)
                ignored = max(0, len([ln for ln in dirty.splitlines() if ln.strip()]) - len(lines))
                if ignored:
                    report.append(f"git_dirty_ignored={ignored}")
                if lines:
                    fails.append("git_dirty:\n" + "\n".join(lines[:40]))
        except Exception as e:
            fails.append(f"git_status: {e}")

    smoke_fails = run_smoke()
    fails.extend(smoke_fails)
    report.append(f"smoke_fails={len(smoke_fails)}")

    extra_fails = run_extra_sites_check()
    fails.extend(extra_fails)
    report.append(f"extra_site_fails={len(extra_fails)}")
    report.append(f"extra_sites={','.join(extra_base_urls())}")

    nginx_fails = run_nginx_eu_vhost_guard()
    fails.extend(nginx_fails)
    report.append(f"nginx_vhost_fails={len(nginx_fails)}")

    phone_fails = run_phone_source_check()
    fails.extend(phone_fails)
    report.append(f"phone_source_fails={len(phone_fails)}")

    maps_fails = run_maps_source_check()
    fails.extend(maps_fails)
    report.append(f"maps_source_fails={len(maps_fails)}")

    ok = len(fails) == 0
    report.append(f"result={'OK' if ok else 'FAIL'}")
    if fails:
        report.append("--- failures ---")
        report.extend(fails)

    text = "\n".join(report)
    print(text)

    out_json = Path(
        os.environ.get("EUADOPT_HEALTHCHECK_LAST_JSON", "/var/lib/euadopt/last_healthcheck.json")
    )
    try:
        out_json.parent.mkdir(parents=True, exist_ok=True)
        out_json.write_text(
            json.dumps(
                {
                    "ok": ok,
                    "time": _now(),
                    "live_sha": live,
                    "expected_sha": exp_sha,
                    "fails": fails,
                    "mode": mode,
                },
                ensure_ascii=False,
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )
    except Exception as e:
        print(f"warn_json: {e}", file=sys.stderr)

    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
