# PT — tabletă portrait touch (FINAL)

**Data:** 2026-07-20  
**Git live:** `3793a9a` — `PT tablet portrait: coloana stanga +25%, grila caini 4x4 cu scroll.`  
**Producție:** Hetzner · https://eu-adopt.ro/pets/

## Scope (doar acest viewport)

```css
@media (min-width: 768px) and (max-width: 64em) and (orientation: portrait) and (hover: none) and (pointer: coarse)
```

**Nu modifică:** telefon portrait ≤767.98px, landscape telefon, desktop mouse.

## Fișier sursă

- `templates/anunturi/pt.html` — bloc CSS inline + `extra_js` (cache `pt382-tablet-4x4-side-w`)
- `static/css/pt-v2.css` — doar `?v=` bump (fără reguli tablet în fișier)

## Layout coloană stângă

- Lățime: `--pt-tab-port-side-w: clamp(5rem, 17.5vw, 8.125rem)` (+25% față de baza 4rem/14vw/6.5rem)
- **Sus 50% (P4):** 2/6 butoane (Găsește-mi · Filtre · Ajută un Suflet) + 1/6 pub P4.3
- **Jos 50% (P5):** 3 pub stivuite (PARTENER + Publi…)
- P4 / P5: `align-self: start` / `end`, înălțime 50% — fără acoperire P5

## Grilă câini (P2)

- **4×4** casete vizibile pe primul ecran
- `--p2-row-h` = înălțime viewport ÷ **4** (minus P1, P3, navbar)
- Scroll în `.pt-p2-scroll`; `pt-p2-more.js` pe tabletă portrait

## Commit-uri sesiune PT tablet (ordine)

1. `abfaeb0` — înălțime viewport  
2. `6cf6861` — pub P5 sub P4.3  
3. `be39b63` — pub compacte  
4. `4fff3f1` — grilă 6 rânduri  
5. `619bd32` — fix display contents  
6. `351f38b` — P5 vizibil jos 50%  
7. `3793a9a` — coloană +25%, 4×4 + scroll  

## Restaurare

Citește blocul `@media` tablet portrait din `pt.html` (~linia 726+). Regulile PT portrait telefon rămân în `PT_MOBIL_PORTRAIT_MEMORAT.mdc` (≤767.98px).
