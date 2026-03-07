# Setări pagină home – referință

*Document de referință pentru setările vizuale pe pagina home. Nu modifică numele paginii sau rutele din proiect.*

---

## ⚠️ HOME = doar home_v2 (nu amesteca cu „home vechi”)

- **Pagina home live:** un singur template – **`anunturi/home_v2.html`** – body class **`page-home-v2`**.
- **Setări A0 / layout home:** folosește **doar** selectorul **`body.page-home-v2`** în CSS. **Nu** folosi `body.page-home` pentru setări live – nu există pagină deservită cu clasa `page-home`.
- **„Home vechi”:** template-ul `home_new.html` (body `page-home`) a fost șters; regulile `body.page-home` rămase în `style.css` sunt moștenire și nu afectează niciun view. La modificări pe home, lucrezi doar cu **home_v2** și **page-home-v2**.

---

## Setări home V2 (corecte) – SETARE FINALĂ SALVATĂ

**Pagina home curentă** folosește **home_v2** (template `home_v2.html`, body class `page-home-v2`, CSS `home_v2.css`). Setările de mai jos sunt cele corecte; la „reparări” care introduc scroll, bară albastră sub A0 sau A4 dezlipit, revii la aceste valori.

**Regulă Cursor (detalii, același rol ca A0):** `.cursor/rules/home-detalii-finale-restart.mdc` – setare finală salvată, punct de restart (ca `a0-detalii-finale-restart.mdc` pentru A0).

### Viewport – fără scroll
- **#main_wrap:** `height: 100vh`, `min-height: 100vh`, `overflow: hidden`, flex column.
- **#main_content:** `flex: 1 1 auto`, `min-height: 0`, `padding-top: 0`.

### A5, A1, A6 lipite de A0 (fără bară albastră)
- **navbar-a0-secured.css:** `body:not(.page-home-v2):not(.page-animale) #main_content { padding-top: var(--nav-height); }` — pe page-home-v2 nu se aplică padding-top, deci conținutul (A5, A1, A6) rămâne lipit de A0.
- **home_v2.css:** `#main_content` — `padding-top: 0`, `margin-top: 0`; `#main_content .layout` — `margin-top: 0`, `padding-top: 0`.

### A1 și A2 – dimensiuni FIXE (din salvare) – **NU SE MODIFICĂ**
- **Sursă:** `undo-point-2026-02-22-1600` (ultima salvare cerută).
- **#A1:** `position: static`, `height: auto`, `min-height: 0`, `max-height: none`. În `.home-v2-center`: `flex-shrink: 0` (A1 își păstrează înălțimea din conținut).
- **#A2:** În `.home-v2-center`: `flex: 1 1 auto`, `min-height: 0`, `overflow-y: auto`, `overflow-x: hidden` (A2 ocupă spațiul rămas, singura zonă cu scroll).
- **INTERZIS:** adăugarea de `min-height`, `height`, `flex: 1` pe A1; schimbarea `flex` sau `min-height` pe A2. Dimensiunile containerelor A1 și A2 rămân neschimbate.
- **La mutare/copiere** conținut dintr-o casetă în alta: se folosesc aceste dimensiuni; dacă nu încape, se **micșorează obiectul mutat**, nu containerul.

### A4 – banda „#EuAdopt#NuCumpar!#”
- Lipită de fundul lui A5, A3, A6: `#A4` — `margin: 0`, `flex-shrink: 0`, fără margin-top negativ.
- Fundal: `#f5e642`; text negru; marquee 45s.

### Containere lipite, fundal albastru
- Gap/margin/padding zero între A0, #main_content, A4 și între A5, A1, A6 (în home_v2.css).
- Fundal albastru `#004B93` pe body, #main_wrap, #main_content, .layout, .home-v2.

### Coloane
- **.home-v2-three-cols:** grid 3 coloane – **coloane laterale vizibile:** `minmax(120px, var(--side-col-width)) | minmax(0, 1fr) | minmax(120px, var(--side-col-width))`; `min-height: calc(100vh - var(--nav-height) - 65px)`. (Fără minmax pe laterale, A5/A6 pot dispărea.)

### A5 și A6 – coloane stânga/dreapta (ID-uri unice + câte 3 casete)
- **ID-uri în template:** `#home-col-left` (stânga), `#home-col-right` (dreapta), `#home-cols-wrap` (grid). Nu folosim #A5/#A6 aici (sidebar din base are #A6 → conflict).
- **#home-cols-wrap:** `display: grid`, `grid-template-columns: 200px 1fr 200px`, `width: 100%`, `min-height: 60vh`, `flex: 1`.
- **#home-col-left, #home-col-right:** `display: flex`, `flex-direction: column`, `min-width: 200px`, `width: 100%`, `background: #c00`, `padding: 6px`, `box-sizing: border-box`.
- **.home-v2-side-inner** (în cele două coloane): `display: grid`, `grid-template-rows: repeat(3, 1fr)`, **`gap: 8px`**, `padding: 0`, `flex: 1`, `min-height: 0`, `height: 100%`, `width: 100%`.
- **.home-v2-slot-white** (cele 3 casete): `background: #fff`, **`min-height: 70px`**, **`border: 2px solid #999`**, **`border-radius: 4px`**, `box-sizing: border-box`.
- Regulile pentru aceste elemente sunt în **blocul `<style>`** din `home_v2.html` (sursă de adevăr). Detalii complete: **.cursor/rules/home-detalii-finale-restart.mdc**.

### Punct de referință – toate dimensiunile și acțiunile home (memorat)
- **A1 – hero:** `.hero-v2` — `padding: 2px 0` (A1 neschimbat); `display: flex`, `align-items: center`, `min-height: 0`. Centrarea siglelor **fără** mărirea A1; dacă nu încape, se micșorează **casetele sigle**, nu A1.
- **Sigle – padding față de laturile A1:** `.hero-v2-inner` — `padding-left: 0.5cm`, `padding-right: 0.5cm` (EU Adopt la 0,5 cm de stânga, transport la 0,5 cm de dreapta).
- **Sigla EU Adopt:** `.hero-v2-logo` — `transform: translateY(-0.3mm)`; logo-img cu `var(--hero-logo-size)`.
- **Sigla transport:** `.hero-v2-transport-badge` — `width` și `height`: `calc(var(--hero-badge-size) + 3mm)`.
- **A5/A6 – 3 casete colorate:** `home-v2-slot-bg1` (#e53935), `home-v2-slot-bg2` (#fdd835), `home-v2-slot-bg3` (#43a047).

### A1 – buton „Hai la noi!” (memorat)
- Link către pagina animale (`pets_all`), text „Hai la noi!”, fundal albastru `#004B93`, text galben `#f5e642`.
- Poziție: centrat, la **0,5 cm** de limita de jos a A1. Clasă: `.hero-v2-cta-animale`.

### A2 – grid promo (memorat)
- **Desktop:** 3 coloane × 3 rânduri (max 9 carduri), gap 0, carduri `aspect-ratio: 4/3`, `min-height: 160px`.
- **Tabletă:** 2 coloane × 4 rânduri (max 8 carduri). **Mobil:** 1 coloană × 6 rânduri (max 6 carduri).
- Fără scroll în A2; coloane lipite (gap 0).

### Fișiere
- **CSS:** `static/css/home_v2.css`
- **Template:** `templates/anunturi/home_v2.html`
- **Excepție navbar:** `static/css/navbar-a0-secured.css` (selector page-home-v2 pentru padding-top).

---

## Setări home (layout vechi – **nefolosit**)

*Istoric: varianta cu sidebare A6/A7/A8 și A12/A13/A14 și body `page-home`. Nu mai există template/view care să folosească `page-home`; HOME = doar home_v2. Regulile `body.page-home` din style.css sunt moștenire și nu se aplică niciodată.*

### Fișier principal (istoric)

- **CSS home vechi:** `static/css/home-sidebar-compact.css` – nu există în proiect.

### Sidebar stânga / dreapta

- **Înălțime coloane:** `calc(100vh - 64px)`
- **Gap între slot-uri:** `2px`
- **Padding slot-container:** `6px`
- **Slot-uri stânga:** A6, A7, A8 — fiecare `flex: 1.28 1 0`, `min-height: 0`, `flex-shrink: 1`
- **Slot-uri dreapta:** A12, A13, A14 — aceleași valori ca stânga
- **.sidebar-box** în slot-uri: `height: 100%`, `flex: 1`, `min-height: 0`

### A2 – Hero / slider + siglă

- **Slider (poze):** `max-height: 260px`, `height: 260px`, `object-fit: cover` pe img
- **Logo final EU-Adopt** (siglă rotundă în A2) – vezi secțiunea dedicată mai jos.
- **Poziție siglă (x home):** `left: calc(1.25cm - 2mm)`, `top: calc(50% + 1mm)`, `transform: translateY(-50%)`, `z-index: 10`

### Logo final EU-Adopt – dimensiuni salvate

**Denumire:** Logo final EU-Adopt  

**Container (A2):**
- `width: 226px`, `height: 226px`
- `border-radius: 50%`, `overflow: hidden`
- `background: #fff`
- Poziție: `left: calc(1.25cm - 2mm)`, `top: calc(50% + 1mm)`, `transform: translateY(-50%)`

**Siglă (imagine în container):**
- `width: 100%`, `height: 100%`
- `object-fit: cover`, `background: #fff`
- `transform: scale(1.40)` (mărire în același container)

**Fișiere:**
- În site: `static/images/logo-final-cu-stele.png`
- Copie pentru refolosit: `poze compas/logo-final-eu-adopt.png`

## A3 – Animalele lunii

- **Link peste celulă:** `position: absolute`, `width/height: 100%`, `left/top: 0`
- **Poze:** `object-fit: cover`, `object-position: center`, `width/height: 100%`
- **Grid:** 4×2 (8 animale), completat până la 8 în view

## Alte setări relevante

- **Logout:** după logout redirecționare la **login** (nu home), ca în mod „site în pregătire” să nu se vadă 503 (`LOGOUT_REDIRECT_URL = "login"` în settings).

---

La modificări ulterioare pe home, folosește acest document și regulile din `.cursor/rules/home-settings-reference.mdc` și **`.cursor/rules/home-detalii-finale-restart.mdc`** (setări finale home_v2, același rol ca a0-detalii-finale-restart.mdc pentru A0) ca referință.
