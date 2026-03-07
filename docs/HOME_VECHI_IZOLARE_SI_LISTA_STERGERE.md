# HOME vechi – eliminat (doar referință)

**Stare actuală:** Ruta `/` folosește **doar** home_v2. HOME vechi a fost eliminat: **home_new.html** a fost șters. Setări home: doar **`body.page-home-v2`** (vezi HOME_SETTINGS_REFERENCE.md). Acest doc rămâne doar ca referință istorică.

---

## 1) Ruta / – doar home_v2

- **anunturi/urls.py:** `path("", home, name="home")` și `path("index.html", home, name="home_index")` trimit la view-ul `home`, care renderează **doar** `anunturi/home_v2.html`.
- Ruta `home-v2/` a fost **eliminată** ca să nu mai existe două URL-uri pentru același conținut (fără clonare).

---

## 2) home_v2 – fără importuri vechi

- **templates/anunturi/home_v2.html** încarcă **doar** `css/home_v2.css` (bloc `{% block extra_css %}`).
- Nu există `include` sau referințe către:
  - `home-sidebar-compact.css`
  - `home-sidebar-promo.js`
  - `home.html` / `home_new.html`
- **base.html** nu încarcă niciun CSS/JS specific home vechi; folosește `style.css` și `navbar-a0-secured.css`; home_v2 adaugă doar `home_v2.css`.

---

## 3) Verificare referințe în proiect

### 3.1) Template-uri și view-uri (Python)

| Ce am verificat | Rezultat |
|-----------------|----------|
| View `home` | Renderează doar `anunturi/home_v2.html` – **OK** |
| Referințe la `home.html` în .py | **Nicio referință** |
| Referințe la `home_new.html` în .py | **Nicio referință** |
| Referințe la `home-sidebar-compact` în .py | **Nicio referință** |

### 3.2) Template-uri HTML

| Fișier | Conținut relevant |
|--------|-------------------|
| home_v2.html | Doar `home_v2.css` – **OK** |
| base.html | Nu încarcă niciun CSS/JS de home vechi – **OK** |

### 3.3) Fișiere care **există** și pot fi șterse după confirmare

| Fișier | Notă |
|--------|------|
| **templates/anunturi/home_new.html** | Template vechi (body_class `page-home`); nu este folosit de niciun view. |

### 3.4) Fișiere menționate în documentație

- `static/css/home-sidebar-compact.css` – **nu există** în `static/css/` (verificat: File not found).
- `static/js/home-sidebar-promo.js` – **nu există** în `static/js/` (nu există niciun fișier home-sidebar*.js).
- `templates/anunturi/home.html` – **nu există** (doar `home_v2.html` și `home_new.html`).

Dacă în alt branch sau în arhivă există `home-sidebar-compact.css` / `home-sidebar-promo.js`, pot fi incluse în lista de ștergere după confirmare. În workspace-ul curent nu sunt prezente.

### 3.5) Documentație care menționează HOME vechi (doar referințe, nu încărcare)

- **LOGO_FINAL_EUADOPT.md** – menționează `home-sidebar-compact.css` ca variantă istorică.
- **HOME_SETTINGS_REFERENCE.md** – menționează `home-sidebar-compact.css` ca „CSS home” (secțiune layout vechi).
- **.cursor/rules/desktop-scale-without-zoom.mdc** – menționează `home-sidebar-compact.css`.
- **GHID_VIDEO_CLIENTI_SIDEBAR.md** – menționează `home-sidebar-promo.js`.
- **TRIMITERE_MODIFICARI_RENDER.md** – exemplu cu `home-sidebar-compact.css`.
- **CONVERSATII_ISTORIC.md**, **HOME_LAYOUT_SKELETON.md**, **DOCUMENTATIE_CENTRALIZATA.md**, **SETARI_LOGO.md** – menționează `home.html` sau `page-home` în context istoric.

Aceste documente **nu încarcă** HOME vechi; doar îl descriu. După confirmare, se poate actualiza textul (ex. „variantă istorică / învechită”) fără ștergere de fișiere.

---

## 4) Listă finală – ce poate fi șters după confirmare

### 4.1) Ștergere efectuată

- **templates/anunturi/home_new.html** – **ȘTERS.** Nu era folosit de niciun view; ruta `/` folosește doar home_v2. Setări home: doar `body.page-home-v2` (vezi HOME_SETTINGS_REFERENCE.md).

### 4.2) Nu există de șters

- `templates/anunturi/home.html` – nu există în proiect.
- `static/css/home-sidebar-compact.css` – nu există.
- `static/js/home-sidebar-promo.js` – nu există.

### 4.3) Opțional – actualizare documentație

După confirmare, în documentele din 3.5 se poate:
- înlocui „home” vechi cu „variantă istorică / învechită” și
- menționa că pagina de acasă este doar home_v2.

---

**Rezumat:** HOME vechi a fost eliminat (home_new.html șters). Ruta `/` folosește doar home_v2. În **style.css** rămân reguli **body.page-home** (moștenire, nefolosite). Pentru modificări pe home folosești doar **page-home-v2**.
