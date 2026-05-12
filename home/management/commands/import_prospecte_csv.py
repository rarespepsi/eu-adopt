"""
Importă unul sau mai multe fișiere CSV în tabelul StaffOnboardingLead (Add USER — prospecte).

Folosește aceeași logică ca upload-ul din interfață (staff_onboarding_csv.import_csv_bytes).

Exemple:
  python manage.py import_prospecte_csv --path "C:\\Users\\USER\\Desktop\\CMVRO_prospecte_judete"
  python manage.py import_prospecte_csv --path "C:\\Users\\USER\\Desktop\\CMVRO_prospecte_judete\\prospecte_AB.csv"
  python manage.py import_prospecte_csv --path "...\\prospecte_AB.csv" --username admin
"""

from __future__ import annotations

from pathlib import Path

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand

from home.staff_onboarding_csv import import_csv_bytes

User = get_user_model()


class Command(BaseCommand):
    help = "Importă CSV prospecte (Add USER) din fișier sau din tot folderul (*.csv)."

    def add_arguments(self, parser):
        parser.add_argument(
            "--path",
            required=True,
            help="Cale către un fișier .csv sau către un folder (se importă toate .csv, sortate după nume).",
        )
        parser.add_argument(
            "--username",
            default="",
            help="Username utilizator pentru created_by (implicit: primul superuser, apoi primul staff).",
        )

    def handle(self, *args, **options):
        raw_path = (options.get("path") or "").strip()
        path = Path(raw_path).expanduser()
        if not path.exists():
            self.stderr.write(self.style.ERROR(f"Cale inexistentă: {path}\n"))
            return

        user = None
        un = (options.get("username") or "").strip()
        if un:
            user = User.objects.filter(username=un).first()
            if not user:
                self.stderr.write(self.style.ERROR(f"Utilizator inexistent: {un!r}\n"))
                return
        if user is None:
            user = User.objects.filter(is_superuser=True).first()
        if user is None:
            user = User.objects.filter(is_staff=True).first()
        if user is None:
            self.stderr.write(
                self.style.ERROR(
                    "Nu există niciun utilizator superuser/staff. Creează unul sau folosește --username.\n"
                )
            )
            return

        if path.is_file():
            files = [path] if path.suffix.lower() == ".csv" else []
        else:
            files = sorted(
                [p for p in path.iterdir() if p.is_file() and p.suffix.lower() == ".csv"],
                key=lambda p: p.name.lower(),
            )

        if not files:
            self.stderr.write(self.style.ERROR("Nu s-a găsit niciun fișier .csv de importat.\n"))
            return

        self.stdout.write(f"created_by: {user.username} (pk={user.pk})\n")
        total_created = 0
        total_ph = 0
        all_errors: list[str] = []

        for fp in files:
            data = fp.read_bytes()
            if len(data) > 5 * 1024 * 1024:
                self.stderr.write(self.style.WARNING(f"Sărit (>{5}MB): {fp.name}\n"))
                continue
            try:
                errors, n, n_ph = import_csv_bytes(data, created_by=user)
            except UnicodeDecodeError:
                self.stderr.write(self.style.ERROR(f"UTF-8 invalid: {fp.name}\n"))
                continue
            except Exception as ex:
                self.stderr.write(self.style.ERROR(f"{fp.name}: {ex}\n"))
                continue

            total_created += n
            total_ph += n_ph
            for e in errors:
                all_errors.append(f"{fp.name}: {e}")
            self.stdout.write(self.style.SUCCESS(f"  {fp.name}: +{n} rânduri (placeholder email: {n_ph})\n"))

        self.stdout.write(self.style.SUCCESS(f"\nTotal importat: {total_created} prospecte.\n"))
        if all_errors:
            preview = "\n".join(all_errors[:20])
            if len(all_errors) > 20:
                preview += f"\n… +{len(all_errors) - 20} altele."
            self.stdout.write(self.style.WARNING(f"Erori / avertismente ({len(all_errors)}):\n{preview}\n"))
