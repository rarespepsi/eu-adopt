"""
Build static/data/ro_counties_cities.json from virgil-av/judet-oras-localitati-romania.
Format: { "Neamț": ["Piatra Neamț", "Roman", ...], "Iași": [...], ... }
Keeps Romanian diacritics.
"""
import json
import urllib.request
from pathlib import Path

from django.core.management.base import BaseCommand

SOURCE_URL = "https://raw.githubusercontent.com/virgil-av/judet-oras-localitati-romania/master/judete.json"
# Normalize cedilla to comma (Romanian standard): ţ->ț, ş->ș
NORMALIZE = str.maketrans({"ţ": "ț", "ş": "ș", "Ţ": "Ț", "Ş": "Ș"})


class Command(BaseCommand):
    help = "Download Romania counties+cities and build ro_counties_cities.json"

    def handle(self, *args, **options):
        base_dir = Path(__file__).resolve().parent.parent.parent.parent
        out_path = base_dir / "static" / "data" / "ro_counties_cities.json"
        out_path.parent.mkdir(parents=True, exist_ok=True)

        self.stdout.write("Fetching %s ..." % SOURCE_URL)
        try:
            with urllib.request.urlopen(SOURCE_URL, timeout=30) as r:
                data = json.loads(r.read().decode("utf-8"))
        except Exception as e:
            self.stderr.write(self.style.ERROR("Download failed: %s" % e))
            return

        judete = data.get("judete") or []
        result = {}
        for j in judete:
            nume = (j.get("nume") or "").strip()
            if not nume:
                continue
            nume = nume.translate(NORMALIZE)
            localitati = j.get("localitati") or []
            cities = []
            seen = set()
            for loc in localitati:
                city = (loc.get("nume") or "").strip()
                if city and city not in seen:
                    city = city.translate(NORMALIZE)
                    cities.append(city)
                    seen.add(city)
            result[nume] = sorted(cities)

        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(result, f, ensure_ascii=False, indent=2)

        self.stdout.write(self.style.SUCCESS("Written %d counties to %s" % (len(result), out_path)))
