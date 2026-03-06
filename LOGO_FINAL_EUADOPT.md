# Logo final EU-Adopt – referință

Dimensiuni și fișiere salvate pentru logo-ul rotund EU-Adopt. Poți copia imaginea din `poze compas/` oriunde ai nevoie.

---

## Fișiere

| Locație | Fișier |
|--------|--------|
| **În proiect (folosit pe site)** | `static/images/logo-final-cu-stele.png` |
| **Copie pentru refolosit** | `poze compas/logo-final-eu-adopt.png` |

Copiază `poze compas/logo-final-eu-adopt.png` acolo unde vrei să folosești același logo.

---

## Varianta veche – container (A2, home vechi)

- **Container:** 226px × 226px, rotund (`border-radius: 50%`), fundal `#fff`
- **Poziție:** `left: calc(1.25cm - 2mm)`, `top: calc(50% + 1mm)`, `transform: translateY(-50%)`
- **Siglă în container:** imagine la `width: 100%`, `height: 100%` cu `transform: scale(1.40)`, `object-fit: cover`, fundal `#fff`, overflow hidden pe container.

CSS (home-sidebar-compact.css – VARIANTĂ ISTORICĂ):
```css
/* Container vechi */
width: 226px;
height: 226px;
border-radius: 50%;
overflow: hidden;
background: #fff;

/* Siglă veche */
width: 100%;
height: 100%;
object-fit: cover;
background: #fff;
transform: scale(1.40);
```

---

## Varianta actuală – HOME_V2 (A1, hero) – CASSETĂ + SIGLĂ = UN TOT UNITAR

Pe `home_v2` sigla este în **A1**, în blocul hero. Caseta rotundă și poza câinelui se tratează **împreună**, ca un singur modul reutilizabil.

### Variabile (în `home_v2.css`)

- `--hero-logo-size`: dimensiunea cercului (containerul rotund).
- `--hero-logo-inner-extra`: **16mm** – cât este poza câinelui **mai mare** decât cercul (zoom în interior). Aici se ajustează „din ochi” cu **plus/minus mm**, fără să mai refacem centrări.

### Container rotund (caseta)

```css
.hero-v2-logo {
    flex-shrink: 0;
    transform: translateY(-0.3mm);
    /* cercul: dimensiune fixă; overflow hidden = mască peste pătratul mărit */
    width: var(--hero-logo-size);
    height: var(--hero-logo-size);
    border-radius: 50%;
    overflow: hidden;
    background: #fff;
    display: flex;
    align-items: center;
    justify-content: center;
}

.hero-v2-logo a {
    /* linkul = pătratul mărit, nu se strânge; cercul (parent) taie ce depășește */
    display: block;
    width: calc(var(--hero-logo-size) + var(--hero-logo-inner-extra));
    height: calc(var(--hero-logo-size) + var(--hero-logo-inner-extra));
    min-width: calc(var(--hero-logo-size) + var(--hero-logo-inner-extra));
    min-height: calc(var(--hero-logo-size) + var(--hero-logo-inner-extra));
    flex-shrink: 0;
}
```

### Poza câinelui + stelele (în casetă)

```css
.hero-v2-logo-img {
    display: block;
    /* pătratul cu sigla: mărime = cerc + extra; cercul taie ce depășește */
    width: calc(var(--hero-logo-size) + var(--hero-logo-inner-extra));
    height: calc(var(--hero-logo-size) + var(--hero-logo-inner-extra));
    min-width: calc(var(--hero-logo-size) + var(--hero-logo-inner-extra));
    min-height: calc(var(--hero-logo-size) + var(--hero-logo-inner-extra));
    flex-shrink: 0;
    /* poziție verticală (0 = centrat; minus = puțin mai sus, plus = puțin mai jos) */
    transform: translateY(0);
    object-fit: cover;
    object-position: center center;
    border-radius: 0;
}
```

### Regulă importantă

- **CASSETĂ + SIGLĂ se folosesc întotdeauna împreună** (blocul `.hero-v2-logo` + `<a>` + `.hero-v2-logo-img`).
- Pe alte pagini, când ai nevoie de sigla EU-Adopt în variantă rotundă, **se copiază întreg modulul** (HTML + CSS de mai sus), nu doar poza și nu se mai „reinventează” centrări pe fiecare pagină.
- Ajustări fine (zoom/poziționare) se fac **doar** prin:
  - `--hero-logo-inner-extra` (mm, zoom în plus față de cerc),
  - `transform: translateY(...)` pe `.hero-v2-logo-img` (sus/jos mm).

---

*Actualizat: variantă HOME_V2 (A1) + variantă veche A2 (istoric).*
