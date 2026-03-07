"""
Raport punctual pentru 3–4 poze-problemă din A2: nume câine, URL imagine, problema în fișier sau în mapping.
Nu modifică CSS. Verifică: margini albe, canvas gol, subiect mic, crop prost, mapping DB.

Rulează: python manage.py raport_poze_a2_problema
"""
import os
from django.core.management.base import BaseCommand
from django.conf import settings

from anunturi.models import Pet


def analizeaza_imagine(path):
    """Returnează dict cu dimensiuni, aspect, și indici pentru margini albe / subiect mic."""
    if not path or not os.path.isfile(path):
        return {"eroare": "Fisier inexistent", "path": path}
    try:
        from PIL import Image
        img = Image.open(path).convert("RGB")
        w, h = img.size
        if w == 0 or h == 0:
            return {"eroare": "Imagine 0x0", "path": path}  # noqa
        aspect = round(w / h, 3)
        # Eșantionare margini: 5% din laturi
        sample = max(1, min(w, h) // 20)
        left = [img.getpixel((x, h // 2)) for x in range(0, sample)]
        right = [img.getpixel((w - 1 - x, h // 2)) for x in range(0, sample)]
        top = [img.getpixel((w // 2, y)) for y in range(0, sample)]
        bottom = [img.getpixel((w // 2, h - 1 - y)) for y in range(0, sample)]

        def medie_lum(pixels):
            return sum(sum(p) for p in pixels) / (3 * len(pixels)) if pixels else 0

        lum_left = medie_lum(left)
        lum_right = medie_lum(right)
        lum_top = medie_lum(top)
        lum_bottom = medie_lum(bottom)
        lum_medie_margini = (lum_left + lum_right + lum_top + lum_bottom) / 4
        # Dacă marginea e foarte luminoasă (> 240) = posibile margini albe
        margini_albe = lum_medie_margini > 240
        # Centru vs margini: dacă centrul e la fel de alb ca marginea = canvas gol/subiect mic
        cx, cy = w // 2, h // 2
        centru = img.getpixel((cx, cy))
        lum_centru = sum(centru) / 3
        canvas_gol_sau_subiect_mic = lum_centru > 235 and lum_medie_margini > 230
        # Raport 4/3 = 1.333
        aspect_43 = abs(aspect - 4 / 3) < 0.05
        return {
            "w": w,
            "h": h,
            "aspect": aspect,
            "aspect_aprox_43": aspect_43,
            "margini_albe": margini_albe,
            "lum_medie_margini": round(lum_medie_margini, 1),
            "lum_centru": round(lum_centru, 1),
            "canvas_gol_sau_subiect_mic": canvas_gol_sau_subiect_mic,
            "path": path,
        }
    except Exception as e:
        return {"eroare": str(e), "path": path}


class Command(BaseCommand):
    help = "Raport punctual: 3–4 poze A2 – nume, URL, problemă în fișier sau mapping."

    def handle(self, *args, **options):
        # Același query ca în home view, fără shuffle (sau seed fix) ca să avem listă reproductibilă
        qs = Pet.objects.filter(status="adoptable").exclude(adoption_status="adopted").order_by("-data_adaugare")[:40]
        pets = list(qs)[:12]
        # Luam primele 4 care au imagine (upload) sau fallback; preferam pe cei cu imagine uploadata
        with_upload = [p for p in pets if p and getattr(p, "imagine", None) and p.imagine]
        with_fallback = [p for p in pets if p and p not in with_upload and getattr(p, "imagine_fallback", None)]
        ordered = list(with_upload)[:4]
        for p in with_fallback:
            if len(ordered) >= 4:
                break
            if p not in ordered:
                ordered.append(p)
        for p in pets:
            if len(ordered) >= 4:
                break
            if p and p not in ordered:
                ordered.append(p)
        ordered = ordered[:4]
        raport = []
        for idx, pet in enumerate(ordered):
            if not pet:
                continue
            i = pets.index(pet) if pet in pets else idx
            sursa = None
            path = None
            url_exact = None
            if pet.imagine:
                sursa = "imagine (upload)"
                try:
                    path = pet.imagine.path
                except Exception:
                    path = None
                url_exact = pet.imagine.url if pet.imagine else None
            elif pet.imagine_fallback:
                sursa = "imagine_fallback (static)"
                # cale statică, ex: images/pets/charlie-275x275.jpg
                static_root = getattr(settings, "STATIC_ROOT", None) or os.path.join(settings.BASE_DIR, "static")
                path = os.path.join(static_root, pet.imagine_fallback.replace("/", os.sep))
                url_exact = f"/static/{pet.imagine_fallback}" if pet.imagine_fallback else None
            else:
                raport.append({
                    "slot": idx + 1,
                    "nume": pet.nume,
                    "pk": pet.pk,
                    "url_imagine": None,
                    "sursa_db": "nici imagine, nici imagine_fallback",
                    "problema": "Mapping: cainele nu are poza setata in DB.",
                    "fisier_ok": False,
                })
                continue

            analiza = analizeaza_imagine(path) if path else {"eroare": "path lipsă", "path": path}
            problema = []
            if "eroare" in analiza:
                problema.append("Fisier: " + analiza["eroare"])
            else:
                if analiza.get("margini_albe"):
                    problema.append("Fisier: margini albe (margini foarte luminoase).")
                if analiza.get("canvas_gol_sau_subiect_mic"):
                    problema.append("Fisier: canvas gol sau subiect foarte mic in centru.")
                if not analiza.get("aspect_aprox_43"):
                    problema.append("Fisier: raport aspect {} (diferit de 4:3).".format(analiza.get("aspect")))
            if not problema:
                problema.append("Fisier: dimensiuni/aspect OK; daca tot se vad spatii, verifica cache sau alt CDN.")

            raport.append({
                "slot": idx + 1,
                "nume": pet.nume,
                "pk": pet.pk,
                "url_imagine": url_exact,
                "path_fisier": path,
                "sursa_db": sursa,
                "analiza": analiza,
                "problema": " ".join(problema) if problema else "Nicio problema evidenta in fisier.",
                "fisier_ok": "eroare" not in analiza and not analiza.get("margini_albe") and not analiza.get("canvas_gol_sau_subiect_mic"),
            })

        # Afișare raport
        self.stdout.write("=" * 60)
        self.stdout.write("RAPORT PUNCTUAL - POZE A2 (3-4 caini)")
        self.stdout.write("=" * 60)
        for r in raport:
            self.stdout.write("")
            self.stdout.write("Caine: {} (pk={}) | Slot A2.{}".format(r["nume"], r["pk"], r["slot"]))
            self.stdout.write("  URL imagine: " + (str(r.get("url_imagine")) if r.get("url_imagine") else "-"))
            self.stdout.write("  Sursa DB: " + (r.get("sursa_db") or "-"))
            if r.get("path_fisier"):
                self.stdout.write("  Cale fisier: " + str(r["path_fisier"]))
            if r.get("analiza") and "w" in r["analiza"]:
                a = r["analiza"]
                self.stdout.write("  Dimensiuni: {}x{} | aspect {} | 4:3? {}".format(a.get("w"), a.get("h"), a.get("aspect"), a.get("aspect_aprox_43")))
                self.stdout.write("  Margini albe (estimare): {} | canvas gol/subiect mic: {}".format(a.get("margini_albe"), a.get("canvas_gol_sau_subiect_mic")))
            self.stdout.write("  Problema: " + r["problema"])
            self.stdout.write("")
        self.stdout.write("=" * 60)
