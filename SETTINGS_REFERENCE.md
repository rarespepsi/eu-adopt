# Referință setări proiect EU-Adopt

Setări stabilite și de păstrat la modificări ulterioare (fără cerere explicită de schimbare).

---

## Autentificare (login)

- **Login cu username SAU email:** câmpul „Utilizator / Email” acceptă atât username cât și adresa de email.
- **Backend:** `anunturi.auth_backends.EmailOrUsernameModelBackend` (în `AUTHENTICATION_BACKENDS`, înainte de `ModelBackend`).
- **Fișier:** `anunturi/auth_backends.py` – dacă inputul conține `@`, se caută user după `email` (case-insensitive); altfel după `username`.

---

## Navbar A0

- **Un singur navbar** pe toate paginile: include `templates/components/navbar_a0.html`.
- **Conținut:** Logo, Acasă, Animale, Servicii, Transport, Shop, Contact; pentru user logat: 👤 username, ❤️ MyPets, ❤️ Te plac (nr), Logout; pentru neautentificat: Intră, Creează cont; pe home: contoare + Termeni și condiții.
- **Base:** `base.html` folosește `{% include "components/navbar_a0.html" %}` în `{% block header %}`.
- Toate paginile cu layout propriu (cont-profil, contact, pets-all, pets-single, login, signup etc.) folosesc același include pentru navbar.

---

## Mod mentenanță (site în pregătire)

- **SITE_PUBLIC** (env): `False` = vizitatorii văd „Site în pregătire” (503).
- **Acces complet** când SITE_PUBLIC=False dacă: (a) user logat și (is_staff sau is_superuser), SAU (b) query `?k=MAINTENANCE_SECRET`, SAU (c) cookie valid setat prin link `/acces-pregatire/<token>/` sau prin `?k=`.
- **MAINTENANCE_SECRET** din `.env`; nu se modifică fără cerere explicită.

---

## Pagina Servicii

- **Wrapper #SW:** de la limita de jos a navbar-ului în jos; `padding-top: var(--nav-height, 56px)`; chenar pe stânga, dreapta și jos, fără border sus.
- **Numerotare casete (memorată):**
  - **1** = banda de sus
  - **2.1, 2.2, 2.3** = cele 3 casete din coloana stânga (2.1 = sus cu selector județ, 2.2 = mijloc, 2.3 = jos)
  - **3** = Cabinete veterinare (centru stânga, grid 3×3 carduri)
  - **4** = Magazine specializate (centru mijloc, grid 3×3)
  - **5** = Saloane cosmetica Vet (centru dreapta, grid 3×3)
  - **6** = caseta din dreapta (galbenă)
  - **7** = banda de jos
- **Subnumerotare planificată (nu implementată încă):** în coloanele 3, 4 și 5 vor exista subnumerotări de tip **3.1, 3.2, 3.3** (și 4.1–4.3, 5.1–5.3) pentru cardurile din grid; se pot adăuga când se dorește.
- **Benzi:** sus și jos fără poze (doar culoare); selector județ în 2.1, precompletat din profil user.

---

## Scală overlay – orientare în cm

- **Regulă:** Scala (jos + dreapta, în cm) rămâne **peste tot** pe paginile unde e instalată (Servicii, Transport, Shop, Contact). La orice conținut nou construit pe aceste pagini, scala trebuie să rămână vizibilă deasupra, pentru orientare.
- **Implementare:** overlay cu `z-index: 99999`, `pointer-events: none`; nu ocupă spațiu în layout. Conținutul nou nu trebuie să aibă z-index mai mare decât scala, ca să nu o acopere.
- **Fișiere:** `static/css/scales-overlay.css`, include `templates/components/scales_overlay.html`; container cu clasa `.page-with-scales` și `position: relative`.

---

## Alte referințe

- **Layout home și sloturi:** vezi `HOME_SETTINGS_REFERENCE.md`.
- **Reguli slot-uri:** doar conținut în sloturi, nu mutarea layout-ului (`.cursor/rules/slot-content-only.mdc`).
