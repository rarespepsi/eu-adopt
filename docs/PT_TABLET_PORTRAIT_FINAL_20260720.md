# PT — tabletă portrait touch (FINAL)

**Data:** 2026-07-20  
**Git live:** `7e3532f` — filtre tablet (portal body, backdrop, bloc P2). Layout 4×4: `3793a9a`.  
**Producție:** Hetzner · https://eu-adopt.ro/pets/  
**Cache:** `pt384-tablet-filters-portal` (`pt.html` + `pt-portrait-ui.js`)

## Scope (doar acest viewport)

```css
@media (min-width: 768px) and (max-width: 64em) and (orientation: portrait) and (hover: none) and (pointer: coarse)
```

**Nu modifică:** telefon portrait ≤767.98px, landscape telefon, desktop mouse.

## Fișiere sursă

| Fișier | Rol |
|-----|-----|
| `templates/anunturi/pt.html` | Bloc CSS inline tablet (~726+) + `extra_js` |
| `static/js/pt-portrait-ui.js` | Filtre portrait; logică tablet: portal + `pt-tab-port-filters-open` |
| `static/css/pt-v2.css` | Doar query string `?v=` |

**Regulă Cursor:** `.cursor/rules/PT_TABLET_PORTRAIT_MEMORAT.mdc`

## Layout coloană stângă

- Lățime: `--pt-tab-port-side-w: clamp(5rem, 17.5vw, 8.125rem)` (+25% față de baza 4rem/14vw/6.5rem)
- **Sus 50% (P4):** 2/6 butoane (Găsește-mi · Filtre · Ajută un Suflet) + 1/6 pub P4.3
- **Jos 50% (P5):** 3 pub stivuite
- P4 / P5: `align-self: start` / `end`, înălțime 50% — fără acoperire P5

## Grilă câini (P2)

- **4×4** casete vizibile pe primul ecran
- `--p2-row-h` = înălțime viewport ÷ **4** (minus P1, P3, navbar)
- Scroll în `.pt-p2-scroll`; `pt-p2-more.js` pe tabletă portrait

## Filtre (confirmat OK utilizator 20 iul 2026)

| Pas | Comportament |
|-----|--------------|
| Deschidere | Buton Filtre → panou fixed, fundal opac, backdrop pe ecran |
| Tap | Nu trece la cardurile P2 (bloc `pointer-events` + portal) |
| Selecție | Tab specie / `<select>` → submit, reload cu filtru; panou rămâne deschis (`pt_filters_open=1`) |
| Închidere | ↑ sau tap pe backdrop |

**Implementare:** panoul `.pt-p4-box-filters` este mutat sub `body` cât timp `body.pt-tab-port-filters-open` (fix Safari/iPad tap-through). Telefon portrait nu folosește portal.

## Commit-uri sesiune PT tablet (ordine)

1. `abfaeb0` — înălțime viewport  
2. `6cf6861` — pub P5 sub P4.3  
3. `be39b63` — pub compacte  
4. `4fff3f1` — grilă 6 rânduri  
5. `619bd32` — fix display contents  
6. `351f38b` — P5 vizibil jos 50%  
7. `3793a9a` — coloană +25%, 4×4 + scroll  
8. `1630029` — încercare pointer-events panou  
9. **`7e3532f`** — **filtre finale: portal, backdrop, bloc P2**  

## Restaurare

Bloc `@media` tablet în `pt.html` + `syncTabPortFiltersChrome` / portal în `pt-portrait-ui.js`. Telefon: `PT_MOBIL_PORTRAIT_MEMORAT.mdc`.
