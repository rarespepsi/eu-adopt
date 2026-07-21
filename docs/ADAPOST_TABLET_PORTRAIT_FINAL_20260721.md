# Fișă adăpost — tabletă portrait touch (FINAL)

**Data:** 2026-07-21  
**Producție:** Hetzner · `ec31aa4` + meta carduri `6a219b0`  
**Regulă Cursor:** `.cursor/rules/ADAPOST_TABLET_PORTRAIT_MEMORAT.mdc`

---

## Viewport

**Tablet portrait touch:** `768px` – `64em`, `(hover: none) and (pointer: coarse)`.

**Tablet landscape touch:** `min-width: 768px`, landscape, touch, `min-height: 600px` (exclude telefon), `max-height: 920px` — același layout 4 casete; **fără** plafon `64em` la lățime (iPad Pro landscape).

---

## Layout

| Stânga | Dreapta |
|--------|---------|
| 4 casete **aceeași înălțime** (1/4 fiecare): adăpost + 3 promo | Grilă **4 coloane × 4 rânduri** vizibile, scroll |
| Lățime `--adp-side-w: clamp(9.25rem, 24vw, 12rem)` | Lipit de stânga, **fără bandă întunecată** (`gap: 0`) |

---

## Dunga (rezolvat)

Cauză: spațiu + fundal pagină `#141a22`. Fix: `gap/column-gap: 0`, subgrid pe `.adp-det__left`, exclude override `821–1100px` pe portrait touch, `@media (max-width: 767.98px)` separat de tabletă.

---

## Carduri câini pe pagină

Sub nume: **localitate · M · vârstă** — vezi `docs/PET_CARD_META_FINAL_20260721.md`.

---

## Fișier unic CSS/HTML

`templates/anunturi/adapost_detail.html` — bloc `extra_css_after` (fără fișier CSS extern / cache bust separat).

---

## Înghețare

**`1977` + OK** pentru orice editare.
