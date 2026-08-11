"""
Actualizează telefonul pe paginile Facebook EU-Adopt (Graph API).

Nu afișează tokenuri. WhatsApp Business pe Page se leagă manual în Meta
dacă API-ul nu permite (necesită WhatsApp Business Account).
"""
from __future__ import annotations

import json
import urllib.error
import urllib.parse
import urllib.request

from django.core.management.base import BaseCommand

from home.euadopt_public_contact import (
    EUADOPT_PUBLIC_PHONE_DISPLAY,
    EUADOPT_PUBLIC_PHONE_E164,
    EUADOPT_WHATSAPP_URL,
)
from home.facebook_markets import FACEBOOK_MARKETS, facebook_graph_version, market_creds


class Command(BaseCommand):
    help = "Setează phone pe paginile Facebook (RO/DE/FR/ES/COM). Fără tokenuri în output."

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Doar citește phone curent, fără POST.",
        )

    def handle(self, *args, **options):
        dry = bool(options["dry_run"])
        version = facebook_graph_version()
        self.stdout.write(f"graph={version} dry_run={dry}")
        self.stdout.write(
            f"phone_set={EUADOPT_PUBLIC_PHONE_E164} display={EUADOPT_PUBLIC_PHONE_DISPLAY}"
        )
        self.stdout.write(f"whatsapp_url={EUADOPT_WHATSAPP_URL}")

        for m in FACEBOOK_MARKETS:
            c = market_creds(m)
            self.stdout.write("---")
            self.stdout.write(f"market={m} page_id={c.page_id or '(empty)'}")
            if not c.configured:
                self.stdout.write(self.style.ERROR("skip=not_configured"))
                continue

            ok_get, before = self._graph_get(
                version, c.page_id, c.access_token, "id,name,phone,website"
            )
            if not ok_get:
                self.stdout.write(self.style.ERROR(f"read_error={before}"))
                continue
            self.stdout.write(
                f"before_phone={before.get('phone') or '(empty)'} name={before.get('name')}"
            )

            if dry:
                self.stdout.write("dry_run_skip_update")
                continue

            ok_post, after = self._graph_post_phone(
                version, c.page_id, c.access_token, EUADOPT_PUBLIC_PHONE_E164
            )
            if not ok_post:
                self.stdout.write(self.style.ERROR(f"update_error={after}"))
                continue
            self.stdout.write(self.style.SUCCESS(f"update_ok={after}"))

            ok2, verify = self._graph_get(
                version, c.page_id, c.access_token, "id,phone"
            )
            if ok2:
                self.stdout.write(f"after_phone={verify.get('phone') or '(empty)'}")

        self.stdout.write("---")
        self.stdout.write(
            "Nota: butonul WhatsApp pe pagină se configurează în Meta Business Suite "
            "(WhatsApp Business) dacă nu apare automat din phone."
        )

    def _graph_get(self, version: str, page_id: str, token: str, fields: str):
        url = (
            f"https://graph.facebook.com/{version}/{page_id}?"
            + urllib.parse.urlencode({"fields": fields, "access_token": token})
        )
        try:
            with urllib.request.urlopen(urllib.request.Request(url, method="GET"), timeout=45) as resp:
                return True, json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            return False, self._err(e)
        except Exception as e:
            return False, f"{type(e).__name__}: {e}"

    def _graph_post_phone(self, version: str, page_id: str, token: str, phone: str):
        url = f"https://graph.facebook.com/{version}/{page_id}"
        body = urllib.parse.urlencode(
            {"phone": phone, "access_token": token}
        ).encode("utf-8")
        try:
            req = urllib.request.Request(url, data=body, method="POST")
            with urllib.request.urlopen(req, timeout=45) as resp:
                return True, json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            return False, self._err(e)
        except Exception as e:
            return False, f"{type(e).__name__}: {e}"

    def _err(self, e: urllib.error.HTTPError) -> str:
        raw = e.read().decode("utf-8", errors="replace")
        try:
            data = json.loads(raw)
            err = data.get("error") or {}
            return f"HTTP {e.code} code={err.get('code')} msg={err.get('message')}"
        except Exception:
            return f"HTTP {e.code} {raw[:200]}"
