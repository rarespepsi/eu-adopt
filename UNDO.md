# Puncte de întoarcere (undo)

---

## PROCEDURA DE REVENIRE (când ceva s-a stricat)

**Când o modificare a stricat containere / layout / setări și vrei înapoi la forma de dinainte:**

1. Deschide terminal în `c:\Users\USER\Desktop` (rădăcina repo-ului, nu în adoptapet_pro).
2. Rulează (înlocuiește tag-ul cu cel la care vrei să revii – vezi listele de mai jos):

```bash
git checkout main
git reset --hard undo-point-2026-02-22-1600
```

3. Gata. Proiectul e exact ca la momentul acelui tag. Modificările făcute după tag se pierd.

**Tag-uri disponibile:** `git tag -l`  
**Cel mai recent (6 martie 2026, final zi):** `undo-point-2026-03-06-2359`

---

# Punct – final zi 6 martie 2026 (P2 toate animalele, scroll 4×3)

**Tag:** `undo-point-2026-03-06-2359`  
**Data:** 6 martie 2026, 23:59  
**Conține:** P2 – toate animalele din site în grid 4 coloane × N rânduri, vizibil 4×3 (aceleași dimensiuni casete), scroll în P2; A2 (Home) 4×3; regula casete-a2-p2.mdc; view p2_pets = list(qs). Casete P2 neschimbate (--pt2-row-h), 4 coloane până la 31.25em.

**Revenire la acest punct:**
```bash
cd c:\Users\USER\Desktop\adoptapet_pro
git checkout main
git reset --hard undo-point-2026-03-06-2359
```
⚠️ Modificările făcute după acest tag se pierd.

---

# Punct – Home badge-uri casete (6 martie 2026)

**Tag:** `undo-point-2026-03-06-2200`  
**Data:** 6 martie 2026, 22:00  
**Conține:** Home – badge-uri numerotate doar pentru staff: A1, A2.1–A2.9, A3, A4, A5.1–A5.3, A6.1–A6.3; A2 poze centrate în casetă; A1 cu poze din featured+strip, A2 shuffle la fiecare încărcare; bloc `extra_css_after` în base; Transport cu fundal, API județ/oraș, link Google Maps. **A4:** badge mic, fără bandă albastră și fără scroll.

**Revenire la acest punct:**
```bash
cd c:\Users\USER\Desktop\adoptapet_pro
git checkout main
git reset --hard undo-point-2026-03-06-2200
```
⚠️ Modificările făcute după acest tag se pierd.

---

# Punct – final de zi 1 martie 2026 (Transport)

**Tag:** `undo-point-2026-03-01-2359`  
**Data și ora:** 1 martie 2026, 23:59  
**Conține:** Pagina Transport: TW cu T1 (formular comandă) și T2; selector județ + oraș din România (ro_counties_cities.json, API ro-counties-cities.json, ro-location.js); dropdown dependente pe Transport și formular înregistrare PF; Places Autocomplete (plecare/sosire). Comandă management: build_ro_counties_cities.

**Revenire la acest punct:**
```bash
cd c:\Users\USER\Desktop
git checkout main
git reset --hard undo-point-2026-03-01-2359
```

---

# Punct – salvare 27 feb 2026

**Tag:** `undo-point-2026-02-27-2100`  
**Data și ora:** 27 februarie 2026, 21:00  
**Conține:** Pagina Prietenul tău (PT): P1 bandă poze sus, P4 (filtre + P4.3), **P2 împărțit în 20 părți egale (grilă 5×4)**, P5 cu 4 casete publicitate numerotate, P3 bandă jos. Layout PW cu pt-v2.css, fără scroll fix pe body. Views: p2_pets (16/20/24) nu se folosește – P2 e doar grila de 20 celule.

**Revenire la acest punct:**
```bash
cd c:\Users\USER\Desktop
git checkout main
git reset --hard undo-point-2026-02-27-2100
```

---

# Punct referință salvare (22 feb 2026)

**Tag:** `undo-point-2026-02-22-1600`  
**Data și ora:** 22 februarie 2026  
**Conține:** Home v2 după modificări pentru mobil: layout responsive (tabletă/mobil), coloane home-col-left/right cu 3 casete, compatibilitate mobil (scroll, touch, imagini max-width), #home-col-left/#home-col-right în reguli compatibilitate. Fără poze în casete. Reguli poze colaboratori, UNDO.md actualizat.

**Revenire la acest punct:**
```bash
cd c:\Users\USER\Desktop
git checkout main
git reset --hard undo-point-2026-02-22-1600
```

---

## Înainte de modificări riscante

Dacă urmează să schimbăm containere / layout / CSS și vrei să poți reveni ușor: spune „salvează punct de undo” sau „creează tag înainte de modificări”. Se creează un tag nou la starea curentă; dacă ceva se strica, revii cu `git reset --hard <noul-tag>`.

---

# Salvare la somn (22 feb 2026)

**Tag:** `undo-point-2026-02-22-2300`  
**Data și ora:** 22 februarie 2026, 23:00  
**Conține:** Home v2 cu A5/A6 (home-col-left, home-col-right), câte 3 casete cu 3 poze în fiecare, setări salvate în home-detalii-finale-restart.mdc (același format ca A0), HOME_SETTINGS_REFERENCE.md actualizat.

## Să revii la acest punct:

**Vedere rapidă (fără să ștergi nimic):**
```bash
cd c:\Users\USER\Desktop
git checkout undo-point-2026-02-22-2300
```
*(revino la main: `git checkout main`)*

**Resetare – proiectul devine exact ca la acest punct:**
```bash
cd c:\Users\USER\Desktop
git checkout main
git reset --hard undo-point-2026-02-22-2300
```
⚠️ Modificările făcute după acest tag se pierd.

**Listează toate tag-urile:** `git tag -l`

---

# Punct de întoarcere (undo) – 17 feb

**Tag:** `undo-point-2026-02-17-2239`  
**Data și ora:** 17 februarie 2026, 22:39  
**Conține:** layout sidebars, paginare animale, signup→register, slot IDs.

## Dacă mâine ai probleme și vrei să revii la acest punct:

**Vedere rapidă (fără să ștergi nimic):**
```bash
cd c:\Users\USER\Desktop
git checkout undo-point-2026-02-17-2239
```
*(revino la branch-ul main după: `git checkout main`)*

**Resetare completă – proiectul devine exact ca la acest punct:**
```bash
cd c:\Users\USER\Desktop
git checkout main
git reset --hard undo-point-2026-02-17-2239
```
⚠️ Orice modificări făcute după acest tag se pierd.

**Listează toate tag-urile:**
```bash
git tag -l
```

---

# Punct de control (22 feb 2026)

**Tag:** `undo-point-2026-02-22-1400`  
**Data și ora:** 22 februarie 2026, 14:00  
**Conține:** Navbar cu contor „În grija noastră” și „Adoptați” în stânga, meniu centrat mutat cu 15 cm la dreapta, lupa în dreapta (-25 cm). My Pets: contoare galbene cu scris verde (animale / în procedura de adoptie / adoptate), filtru după cerere aprobată. Layout cont ONG / cont profil (stânga date + poză, dreapta grid 4 coloane).

## Să revii la acest punct:

**Vedere rapidă (fără să ștergi nimic):**
```bash
cd c:\Users\USER\Desktop
git checkout undo-point-2026-02-22-1400
```
*(revino la main: `git checkout main`)*

**Resetare – proiectul devine exact ca la acest punct:**
```bash
cd c:\Users\USER\Desktop
git checkout main
git reset --hard undo-point-2026-02-22-1400
```
⚠️ Modificările făcute după acest tag se pierd.

---

# Salvare Transport (punct întoarcere)

**Tag:** `transport`  
**Data:** 18 februarie 2026  
**Conține:** Pagina Transport finală – casete 1–19 numerotate roșu, sigle A2 (alternanță 3 s), bloc „Poți ajuta un câine” + Card/SMS fix la 3 cm dreapta, fără video în sidebar, A6 gol, buton Servicii în navbar, link siglă autocar → Transport.

## Să revii la această salvare:

**Vedere rapidă (fără să ștergi nimic):**
```bash
cd c:\Users\USER\Desktop
git checkout transport
```
*(revino la main: `git checkout main`)*

**Resetare – proiectul devine exact ca la salvare Transport:**
```bash
cd c:\Users\USER\Desktop
git checkout main
git reset --hard transport
```
⚠️ Modificările făcute după acest tag se pierd.
