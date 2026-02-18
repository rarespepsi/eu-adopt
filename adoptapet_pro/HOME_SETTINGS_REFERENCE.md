# Setări pagină home – referință „foarte bune”

*Memorate la 18 februarie 2026. Aceste setări sunt considerate optime; păstrează-le la modificări decât dacă se cere altfel.*

## Fișier principal

- **CSS home:** `static/css/home-sidebar-compact.css` (încărcat ultimul pe pagina home)

## Sidebar stânga / dreapta

- **Înălțime coloane:** `calc(100vh - 64px)`
- **Gap între slot-uri:** `2px`
- **Padding slot-container:** `6px`
- **Slot-uri stânga:** A6, A7, A8 — fiecare `flex: 1.28 1 0`, `min-height: 0`, `flex-shrink: 1`
- **Slot-uri dreapta:** A12, A13, A14 — aceleași valori ca stânga
- **.sidebar-box** în slot-uri: `height: 100%`, `flex: 1`, `min-height: 0`

## A2 – Hero / slider + siglă

- **Slider (poze):** `max-height: 260px`, `height: 260px`, `object-fit: cover` pe img
- **Siglă rotundă:** vizibilă (`display: block`), nu ascunsă
- **Poziție siglă:**
  - `left: -0.75cm` (0,75 cm în afara zonei A2 spre stânga)
  - `top: calc(50% + 1.25cm)` (cu 1,25 cm sub centrul vertical)
  - `transform: translateY(-50%)`
  - `margin-left: 0`

## A3 – Animalele lunii

- **Link peste celulă:** `position: absolute`, `width/height: 100%`, `left/top: 0`
- **Poze:** `object-fit: cover`, `object-position: center`, `width/height: 100%`
- **Grid:** 4×2 (8 animale), completat până la 8 în view

## Alte setări relevante

- **Logout:** după logout redirecționare la **login** (nu home), ca în mod „site în pregătire” să nu se vadă 503 (`LOGOUT_REDIRECT_URL = "login"` în settings).

---

La modificări ulterioare pe home, folosește acest document și regula din `.cursor/rules/home-settings-reference.mdc` ca referință.
