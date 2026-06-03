"""
Citește inbox IMAP (Zoho) și marchează răspunsuri / bounce la prospecte Add USER.

Necesită în .env:
  STAFF_INVITE_IMAP_HOST=imappro.zoho.eu
  STAFF_INVITE_IMAP_USER=contact@eu-adopt.ro
  STAFF_INVITE_IMAP_PASSWORD=...

Rulare:
  python manage.py staff_invite_poll_inbox
  python manage.py staff_invite_poll_inbox --max 20 --dry-run
"""
from django.core.management.base import BaseCommand

from home.staff_onboarding_invite_inbound import poll_imap_inbox, staff_invite_imap_configured


class Command(BaseCommand):
    help = "Procesează emailuri noi (IMAP) pentru invitații Add USER — răspuns / bounce / opt-out."

    def add_arguments(self, parser):
        parser.add_argument("--max", type=int, default=40, help="Max. mesaje UNSEEN de procesat.")
        parser.add_argument(
            "--no-mark-seen",
            action="store_true",
            help="Nu marca mesajele ca citite în IMAP.",
        )

    def handle(self, *args, **options):
        if not staff_invite_imap_configured():
            self.stderr.write(
                "IMAP neconfigurat. Setează STAFF_INVITE_IMAP_HOST, STAFF_INVITE_IMAP_USER, "
                "STAFF_INVITE_IMAP_PASSWORD în .env."
            )
            return
        stats = poll_imap_inbox(
            max_messages=max(1, options["max"]),
            mark_seen=not options["no_mark_seen"],
        )
        if stats.get("error") and stats.get("message"):
            self.stderr.write(str(stats["message"]))
        self.stdout.write(self.style.SUCCESS(str(stats)))
