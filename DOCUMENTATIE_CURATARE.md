# Plan de curățare proiect – unic, fără dubluri

**Scop:** Tot ce rămâne în proiect să fie unic. Fără comenzi/reguli dublate sau triplate care blochează layout (ex. 4×3 casete egale). Doar HOME + navbar universal + restul paginilor curate.

---

## Reguli proiect – vechi nu trebuie să ne încurce

**De aplicat mereu, pe viitor:**

- Orice e **vechi** și **ne încurcă** nu rămâne în codul activ.
- Se **mută** în fișiere doar de **informare** sau **proceduri vechi** (ex. `_archive/`, `_old/`, docs, README).
- Rămân **ca idee / referință**, dar **nu mai pot influența** execuția.

**Scurt:** Vechiul = documentare sau arhivă. Activul = doar ce folosim acum, fără condiții care să ne blocheze.

Când dăm peste ceva vechi care stă în cale: mutare în fișier de informare / proceduri vechi (sau ștergere la sursă), nu doar override. Exemplu rezolvat: `aspect-ratio: 4/3` pe P2 în pet-images-common.css – șters la sursă, nu doar suprascris.

---

## 1. Ce este în uz (singura sursă de adevăr)

| Rol | Fișier / cale |
|-----|----------------|
| **HOME** | `templates/anunturi/home_v2.html` (extends base.html), `static/css/home_v2.css` |
| **Navbar (A0)** | `templates/components/navbar_a0.html`, `static/css/navbar-a0-secured.css` |
| **Prietenul tău (P2)** | `templates/anunturi/pt.html`, `static/css/pt-v2.css` – grid 4×3 în `.pt-p2-viewport` |
| **Base** | `templates/base.html` – layout 3 coloane, sidebar left/right, block content |
| **Views** | `home/views.py` – home_view (home → home_v2; pets_all → pt.html), dog_profile_view → pets-single |
| **URLs** | `home/urls.py` – toate rutele; celelalte (servicii, transport, etc.) trimit la home_view → home_v2 (placeholder) |

---

## 2. Duplicat / moarte – de curățat

### 2.1 CSS navbar – dublat
- **`navbar-a0-secured.css`** – folosit în `base.html` → **păstrat**.
- **`navbar-a0-secured-FROM-SAVE.css`** – copie veche, referință la `.cursor/rules/` → **șters** (sau redenumit .bak dacă vrei backup). Proiectul nu mai depinde de el.

### 2.2 CSS P2 (pt-v2.css) – reguli care se pot contrazice
- **`.pt-p2-viewport`** – grid 4×3 egal (4 col × 3 rânduri egale) → **singura regulă pentru grid-ul vizibil P2. PĂSTRAT.**
- **`.pt-p2-rest`** – pentru rânduri sub viewport (scroll), `grid-auto-rows: 220px` → păstrat (alt scop).
- **`.pt-p2-20grid`** – `grid-auto-rows: 140px`; **nu e folosit în pt.html** (în pt.html există doar `pt-p2-viewport`). E moarte/legacy și poate confunda (dacă s-ar aplica undeva, rupe 4×3 egal). → **Eliminat** (sau comentat cu „legacy – nu folosi”).

### 2.3 Template moarte
- **`templates/anunturi/pets-all.html`** – **nu e randat nicăieri** (views folosesc doar `pt.html` pentru `/pets/`). E variantă veche, HTML standalone. → **Șters** sau mutat în `_archive/` ca să nu mai fie în calea execuției.
- **`templates/animals/prietenul_tau_v2.html`** – nu e referit în views. → Poate fi arhivat/șters.

### 2.4 base.html – bloc A2 duplicat
- În `base.html`, blocul `{% if a2_pets %} … A2-casete-wrap … {% endif %}` **nu e folosit** pentru HOME, pentru că `home_v2.html` suprascrie tot `block content` cu propria structură (inclusiv A2). Deci A2 din base este cod mort pentru fluxul actual. → **Eliminat** din base (păstrăm doar block content gol sau minimal), ca să nu existe două definiții A2.

### 2.5 Fișiere doar documentație / analiză (nu le ștergem, le memorăm)
- `EUADOPT_STRUCTURE.md` – reguli proiect.
- `P2_LAYOUT_LOCKED.md`, `HOME_LAYOUT_LOCKED.md`, `home/HOME_SLOTS.md` – layout înghețat.
- `static/images/pets/HERO_IMAGES_SURSE.md` – surse imagini.
- Acest fișier – plan și detalii curățare.

---

## 3. Pași executați la curățare (făcut)

1. **Navbar:** Șters `navbar-a0-secured-FROM-SAVE.css`. Singura sursă A0: `navbar-a0-secured.css`.
2. **pt-v2.css:** Eliminat blocul `.pt-p2-20grid` / `body.page-animale #PW .pt-p2-20grid` (grid-auto-rows: 140px). Rămâne doar `.pt-p2-viewport` pentru 4×3 egal și `.pt-p2-rest` pentru rânduri sub viewport.
3. **base.html:** Eliminat blocul duplicat A2 din `block content` și link-ul condiționat `{% if a2_pets %} home_v2.css` (home_v2.html îl încarcă în `extra_css`).
4. **Templates moarte:** Șters `templates/anunturi/pets-all.html` (nu era randat de niciun view).

După acești pași, nu mai există două/trei surse pentru același layout (navbar, A2, P2 grid), iar 4×3 egal rămâne definit într-un singur loc clar.

### 3.2 Curățare atentă (mutare în _archive)

**Template-uri** mutate în `templates/_archive/`:
- `anunturi/`: servicii, transport, shop, contact, termeni, cauta, cont-*, beneficii-adoptie*, match_*, wishlist*, adoption_*, analiza*, my-posted-pets, pet-ask, verificare-post-adoptie, membri-list, schema-site, beneficii_partner_card (includes)
- `registration/`: toate (login, signup, register_*, password_reset_*)
- `components/`: scales_overlay.html
- `animals/`: prietenul_tau_v2.html
- maintenance.html

**CSS** mutate în `static/css/_archive/`: transport.css, auth-pages.css, pets-all-debug.css, prietenul-tau-v2.css, scales-overlay.css

**JS** mutat în `static/js/_archive/`: measure-home-layout.js, ro-location.js, auth-form-errors.js  
**JS** mutat în `static/includes/js/_archive/`: rescue.js, jquery.sticky.js, jquery.mobilemenu.js

În fiecare `_archive` există README.md care explică conținutul. Fișierele pot fi restaurate când se vor folosi din nou paginile respective.

### 3.4 Scoatere elemente vechi cu salvare ca material de informare (martie 2026)

- **Rute URL:** Rutele placeholder (servicii, transport, shop, login, contact, analiza, wishlist, cont, profil etc.) au fost scoase din `home/urls.py`. Rămân active doar: `''` (home), `pets/`, `pets/<int:pk>/`. Lista completă a rutelor scoase este în `_archive/URLS_PLACEHOLDER_ARCHIVED.md`.
- **CSS burtiera și layout animale vechi:** Regulile pentru `#burtiera_mica`, `#burtiera_jos`, `#A1 #burtiera_mica`, `#burtiera_mica + .container` și regulile burtiera din @media (56.25em, 37.5em, 24em) au fost scoase din `style.css` și salvate în `static/css/_archive/style-old-burtiera-animale-layout.css` (doar referință, nu este încărcat).

### 3.5 Opțional – curățare viitoare
- **style.css** mai poate conține clase legacy nefolosite de pt.html (ex. `pets-all-no-img`). Burtiera a fost deja arhivată.

---

*Documentație curățare – martie 2026*
