# Setări pagină PT (Prietenul tău / pets-all) – referință

*Document de referință pentru setările vizuale și responsive pe pagina „Prietenul tău” (/pets-all). La modificări pe PT, păstrează aceste valori dacă utilizatorul nu cere explicit altceva.*

---

## Pagina PT

- **Rută:** `/pets-all` (view `pets_all`).
- **Body class:** `page-animale`.
- **Template:** `templates/anunturi/pets-all.html`.
- **CSS principal:** `static/css/pt-v2.css` (încărcat după style.css, navbar, pets-all-debug.css).

---

## Layout principal (desktop)

- **#main_wrap:** `height: 100dvh`, `min-height: 100dvh`, `overflow: hidden`, `display: flex`, `flex-direction: column`, **`padding-bottom: 0 !important`** (fără bandă sub P3; style.css punea `calc(72px + 3mm)`).
- **#main_content:** `flex: 1 1 auto`, `min-height: 0`, `display: flex`, `flex-direction: column`.
- **#PW:** `flex: 1 1 auto`, `min-height: 0`, `overflow: hidden`.
- **.pt-grid:** `grid-template-columns: 0.26fr 3.24fr 0.5fr` (P4 | P2 | P5); `grid-template-rows: minmax(72px, 0.28125fr) 2.4375fr minmax(72px, 0.28125fr)`; `height: 100%`; `min-height: 300px`; `gap: 0`.

### Celule

- **P1 (bandă sus):** grid row 1, col 1/4; `min-height: 72px`; fundal `#1565c0`; strip animat stânga→dreapta.
- **P4 (filtre stânga):** grid row 2, col 1; padding 4px.
- **P2 (listă animale):** grid row 2, col 2; `overflow-y: auto`, `overflow-x: hidden`, `min-height: 0`; `--pt2-row-h: calc((100% - 8px) / 3)` (3 rânduri vizibile).
- **P5 (reclame dreapta):** grid row 2, col 3; 4 casete egale.
- **P3 (bandă jos):** grid row 3, col 1/4; `min-height: 72px`; fundal `#2e7d32`.

### P2 – listă animale

- **Desktop:** `grid-template-columns: repeat(5, minmax(0, 1fr))`; `grid-auto-rows: var(--pt2-row-h)`; `gap: 4px`. Scroll doar în P2.

---

## Breakpoint-uri responsive (ca pe home v2, în em)

- **56.25em** ≈ 900px – tabletă.
- **37.5em** ≈ 600px – mobil.
- **31.25em** ≈ 500px – mobil îngust (layout stivuit + hamburger).

### Tabel coloane P2 / layout

| Viewport        | Coloane P2 | Layout PW      | P1/P3              | Hamburger P4 |
|-----------------|------------|----------------|--------------------|--------------|
| > 56.25em       | 5          | P4 \| P2 \| P5 | min 72px (fr)      | ascuns       |
| ≤ 56.25em       | 4          | P4 \| P2 \| P5 | neschimbat         | ascuns       |
| ≤ 37.5em        | 3          | P4 \| P2 \| P5 | fix 72px           | ascuns       |
| ≤ 31.25em       | 2          | stivuit        | max 72px           | vizibil      |

### Reguli pe breakpoint

**56.25em (tabletă):** doar 4 coloane P2 + `min-width: 0` pe grid și pe .pt-cell-2, .pt-cell-4, .pt-cell-5. **Nu se modifică P1/P3.**

**37.5em (mobil, 3 coloane):**
- `.pt-grid`: `grid-template-rows: 72px 1fr 72px` (rânduri 1 și 3 fixe 72px).
- P1/P3: `min-height: 72px`, `max-height: 72px`, `height: 72px`, `overflow: hidden`, `flex-shrink: 0`; idem pentru `.pt-strip-wrap` și `.pt-strip-item--p1` / `--p3`.
- P2: 3 coloane; `.pt-p2-num` vizibil (visibility, opacity, z-index).

**31.25em (mobil îngust, stivuit):**
- `#main_wrap`: `height: auto`, `min-height: 100vh`, `overflow-y: auto`.
- `.pt-grid`: `grid-template-columns: 1fr`, `grid-template-rows: auto`, toate celulele `grid-column: 1`, `grid-row: auto`.
- P2: 2 coloane; `--pt2-row-h: 80px`; `min-height: 280px`, `max-height: 50vh`.
- P4: hamburger afișat; panoul filtre ascuns implicit, vizibil la `.is-open`.
- P1/P3: `max-height: 72px`; P4/P5: `min-height: 120px`.

**Hamburger:** ascuns cu `@media (min-width: 31.25em)`; vizibil doar sub 31.25em.

---

## Navbar (A0) – același pe toate paginile

- **Un singur component:** `templates/components/navbar_a0.html` – folosit pe PT, Home, Servicii și toate celelalte pagini.
- **Setările de pe PT (și Home) sunt etalonul** pentru aspectul navbar-ului; la reparări sau unificări se folosesc aceste valori. Vezi `a0-detalii-finale-restart.mdc` și `navbar-a0-secured.css`.

---

## Fișiere

- **CSS:** `static/css/pt-v2.css`
- **Template:** `templates/anunturi/pets-all.html`
- **Referință home (breakpoint-uri em):** `HOME_SETTINGS_REFERENCE.md`, `static/css/home_v2.css`

---

## Punct de restart

La „reparări” pe PT care reintroduc scroll pe body, bandă sub P3, deformare la 5→4 sau 4→3 coloane, revino la valorile din acest document și din `pt-v2.css`.
