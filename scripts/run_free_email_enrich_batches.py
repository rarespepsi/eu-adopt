"""Loturi staff_lead_free_email_enrich — prioritate lead-uri cu website în notes."""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BATCH = 200
COUNT_PY = """
from django.db.models import Q
from home.models import StaffOnboardingLead
n = StaffOnboardingLead.objects.filter(
    Q(email__iendswith='@lead-placeholder.invalid') | Q(email='')
).exclude(notes__contains='[FREE_EMAIL_ENRICH').count()
print(n)
"""


def remaining() -> int:
    env = {**os.environ, "PYTHONIOENCODING": "utf-8"}
    r = subprocess.run(
        [sys.executable, "manage.py", "shell", "-c", COUNT_PY],
        cwd=ROOT,
        capture_output=True,
        text=True,
        env=env,
    )
    r.check_returncode()
    return int(r.stdout.strip().splitlines()[-1])


def main() -> int:
    os.chdir(ROOT)
    env = {**os.environ, "PYTHONIOENCODING": "utf-8"}
    batch_no = 0
    while True:
        left = remaining()
        if left <= 0:
            print("Gata — 0 lead-uri fără FREE_EMAIL_ENRICH.")
            return 0
        batch_no += 1
        print(f"=== Free enrich lot {batch_no} | rămase {left} | max {BATCH} ===", flush=True)
        rc = subprocess.run(
            [
                sys.executable,
                "manage.py",
                "staff_lead_free_email_enrich",
                "--limit",
                str(BATCH),
                "--apply",
            ],
            cwd=ROOT,
            env=env,
            stderr=subprocess.DEVNULL,
        )
        if rc.returncode != 0:
            print(f"Lot {batch_no} exit {rc.returncode}", flush=True)
            return rc.returncode
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
