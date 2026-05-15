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
import shlex

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.utils import timezone

from home.staff_onboarding_csv import import_csv_bytes

User = get_user_model()


def _write_import_marker(
    csv_path: Path,
    *,
    user,
    rows_created: int,
    placeholder_emails: int,
    errors: list[str],
) -> None:
    """Lângă fiecare CSV importat: `<nume>.imported` (text) — semn că a trecut prin import_prospecte_csv."""
    marker_path = csv_path.parent / f"{csv_path.name}.imported"
    lines = [
        "# EU-ADOPT — marker import StaffOnboardingLead (Add USER)",
        f"imported_at_utc: {timezone.now().isoformat()}",
        f"source_csv: {csv_path.name}",
        f"rows_created: {rows_created}",
        f"placeholder_emails: {placeholder_emails}",
        f"created_by: {user.username} (pk={user.pk})",
        f"django_command: import_prospecte_csv --path {shlex.quote(str(csv_path))}",
    ]
    if errors:
        lines.append(f"errors_count: {len(errors)}")
        lines.append("errors_preview:")
        for e in errors[:15]:
            lines.append(f"  - {e}")
        if len(errors) > 15:
            lines.append(f"  … +{len(errors) - 15} altele")
    marker_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


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
            try:
                _write_import_marker(fp, user=user, rows_created=n, placeholder_emails=n_ph, errors=errors)
                self.stdout.write(f"  → semn import: {fp.name}.imported\n")
            except OSError as ex:
                self.stderr.write(self.style.WARNING(f"  Nu s-a putut scrie markerul .imported: {ex}\n"))
        self.stdout.write(self.style.SUCCESS(f"\nTotal importat: {total_created} prospecte.\n"))
        if all_errors:
            preview = "\n".join(all_errors[:20])
            if len(all_errors) > 20:
                preview += f"\n… +{len(all_errors) - 20} altele."
            self.stdout.write(self.style.WARNING(f"Erori / avertismente ({len(all_errors)}):\n{preview}\n"))
