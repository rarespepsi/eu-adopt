# Poziții butoane și casete – navbar Home (A0)

*Referință: toate pozițiile (padding, margin, left, right, dimensiuni) pentru butoane și casete din navbar pe pagina Home (body.page-home-v2). Sursă: `static/css/navbar-a0-secured.css`, `static/css/style.css`.*

---

## Variabile CSS (style.css, body)

| Variabilă | Valoare | Folosire în A0 |
|-----------|---------|----------------|
| `--nav-height` | `clamp(48px, 10vw, 64px)` | Înălțime A0, container, meniu, contor, linkuri |
| `--gap-v2` | `clamp(8px, 2vw, 16px)` | Spațiu între itemi meniu: `margin-left: calc(var(--gap-v2) / 4)` pe `ul li` |
| `--btn-padding-h` | `clamp(12px, 3vw, 24px)` | Padding orizontal linkuri: `calc(var(--btn-padding-h) / 3)` pe `ul li a` |
| `--side-col-width` | `min(200px, 25vw)` | (menționat în comentarii; contorul e acum absolut) |

---

## Home (page-home-v2) – valori specifice

### Container A0

| Element | Proprietate | Valoare |
|---------|-------------|---------|
| `#A0 .container` | padding-left | **2cm** |
| `#A0 .container` | padding-right | **6cm** |
| `#A0 .container` | height / min-height / max-height | `var(--nav-height)` |
| `#A0 .container` | margin | 0 auto |

*Pe alte pagini (nu home/PT):* padding-left 7cm.

---

### Contor (.a0-left, .animal-counter-navbar.a0-counters-left)

| Element | Proprietate | Valoare |
|---------|-------------|---------|
| `.a0-left` | position | **absolute** |
| `.a0-left` | left | **-2cm** (pe home; în zona de padding) |
| `.a0-left` | top | 0 |
| `.a0-left` | margin-left | 0 |
| `.a0-left` | max-width | 20cm |
| `.a0-left` | height | 100% |
| `.animal-counter-navbar.a0-counters-left` | margin-left | 0 |
| `.animal-counter-navbar.a0-counters-left` | gap | 2px |
| `.animal-counter-navbar.a0-counters-left .counter-item` | gap | 6px |
| Contor – label | font-size | 13px |
| Contor – value | font-size | 22px, font-weight 800 |
| Contor – icon | font-size | 20px |

---

### Meniu (#menu_wrap) și butoane (Acasă, Prietenul tău, Servicii, etc.)

| Element | Proprietate | Valoare |
|---------|-------------|---------|
| `#menu_wrap` | margin | **0** (butoanele rămân fixe, contorul nu le deplasează) |
| `#menu_wrap` | padding | 0 |
| `#menu_wrap` | position | (în flux, nu absolut) |
| `ul#menu-main-menu` | margin | 0 |
| `ul#menu-main-menu` | padding | 0 |
| `#A0 #main_menu ul li` | margin-left | **calc(var(--gap-v2) / 4)** |
| `#A0 #main_menu ul li` | (vechi, suprascris) | margin: 0 0 0 15px (în regulă ul li de mai sus e calc) |
| `#A0 #main_menu ul li a` | padding | **0 calc(var(--btn-padding-h) / 3)** |
| `#A0 #main_menu ul li a` | font-size | 13px |
| `#A0 #main_menu ul li a.current_page` | padding | **0 10px** |
| `#A0 #main_menu ul li a.current_page` | border-radius | 6px |
| `#A0 #main_menu ul li a.current_page` | line-height | 36px |

---

### Căutare (.a0-search-right)

| Element | Proprietate | Valoare |
|---------|-------------|---------|
| `.a0-search-right` | position | **absolute** |
| `.a0-search-right` | right | **-6cm** (în zona padding-right a containerului) |
| `.a0-search-right` | gap | 6px |
| `#searchform #s` (input) | width / min-width | **5cm** |
| `#searchform #s` | height | 32px |
| `#searchform #s` | padding | 0 28px 0 6px |
| `#searchform #s` | font-size | 13px |
| `#searchform #s` | border-radius | 4px |
| `.a0-search-submit` (buton) | position | absolute, top 50%, **right 4px** |
| `.a0-search-submit` | width / height | 22px |
| Căutare expandată (`.a0-search-expanded`) | width #s | 15cm, max-width min(15cm, 40vw), min-width 4cm |
| `.a0-search-history` (dropdown) | top | 100% |
| `.a0-search-history` | left / right | 0 |
| `.a0-search-history` | margin-top | 2px |
| `.a0-search-history` | padding | 4px 0 |

---

### A0 (header) – comun

| Element | Proprietate | Valoare |
|---------|-------------|---------|
| `#A0` (pe home) | position | **relative** (în flux; nu fixed) |
| `#A0` | height / min-height / max-height | `var(--nav-height)` |
| `#A0` | background-color | #343434 |
| `#A0 #main_menu` | padding / margin | 0 |
| `#A0 #main_menu .a0-bar-inner` | position | relative |
| `#A0 #main_menu .a0-bar-inner` | width | 100% |
| `#A0 #main_menu .a0-bar-inner` | justify-content | flex-start |

---

### Alte casete / elemente în A0

| Element | Proprietate | Valoare |
|---------|-------------|---------|
| `.wishlist-nav-box.a0-wishlist-badge` | margin-left | 12px |
| `.wishlist-nav-box.a0-wishlist-badge` | padding | 6px 12px |
| `.wishlist-nav-box.a0-wishlist-badge` | border-radius | 8px |
| `.wishlist-nav-box .wishlist-nav-count` | font-size | 18px |
| `.a0-mobile-trigger` (hamburger) | padding | 10px 12px |
| `.a0-mobile-trigger` | display | none (desktop); flex (mobil ≤37.5em) |
| `.a0-hamburger` | width / height | 22px, 18px |

---

## Mobil (max-width: 37.5em ≈ 600px)

| Element | Proprietate | Valoare |
|---------|-------------|---------|
| `#A0 .container` | padding-left / padding-right | **12px** |
| `.a0-left` | display | **none** (contor ascuns) |
| `.a0-search-right` | position | static |
| `.a0-search-right` | right | auto |
| `.a0-search-right` | margin-left | auto |
| `#searchform #s` | width | 120px |
| `#searchform #s` | min-width | 80px |
| `#searchform #s` | max-width | 40vw |
| `#menu_wrap` | position | fixed |
| `#menu_wrap` | top | var(--nav-height) |
| `#menu_wrap` | left / right | 0 |
| `#menu_wrap` | padding | 16px 0 |
| `#menu_wrap` | display | none (deschis la .a0-nav-open) |
| `ul.menu` | padding | 0 12px |
| `ul.menu li a` | padding | 14px 12px |
| `ul.menu li a` | font-size | 15px |

---

## Fișiere

- **CSS navbar:** `static/css/navbar-a0-secured.css`
- **Variabile globale:** `static/css/style.css` (body: --nav-height, --gap-v2, --btn-padding-h)
- **Template navbar:** `templates/components/navbar_a0.html`

---

*Actualizat: referință pentru toate pozițiile butoane și casete pe navbar Home.*
