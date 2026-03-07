# Raport audit – sistem imagini (CSS)

**Data:** martie 2026  
**Scop:** identificare reguli CSS care afectează imaginile (background-image, img, object-fit, background-size, transform scale, hover zoom, max-width, max-height) și raportare conflicte / câștigători per pagină.

---

## Ordinea încărcării CSS (relevante pentru imagini)

| Pagină | Ordine fișiere |
|--------|----------------|
| **HOME (A2)** | `style.css` → `home_v2.css` (block extra_css) → `navbar-a0-secured.css` → `pet-images-common.css` |
| **Fișa câinelui (pets-single)** | `style.css` → `navbar-a0-secured.css` → `pet-images-common.css` → flexslider, fancybox |
| **Prietenul tău (pets-all, P2 + grid)** | `style.css` → `navbar` → `pt-v2.css` → `pet-images-common.css` → flexslider, fancybox |

---

## 1. Reguli care se bat cap în cap

### 1.1 `img` generic vs. reguli specifice

- **style.css (linia ~92):** `img { max-width: 100%; height: auto; }` – se aplică la toate imaginile. Pe pagini unde imaginile sunt în containere cu înălțime fixă și se folosește `object-fit: cover`, `height: auto` poate intra în conflict cu „umplerea” casetei.
- **Pe body.page-animale:** `body.page-animale img { max-width: 100% !important; height: auto !important; }` (style.css ~2651) intră în conflict cu `body.page-animale #PW img { width: 100%; height: 100%; max-width: none; object-fit: cover; }` (style.css ~2656) și cu `#all_pets_wrap.pets-grid img.attachment-pet_single_large { max-width: none; ... }` (style.css ~3374, 2664). **Câștigă** regulile mai specifice (#PW img, .pets-grid img.attachment-pet_single_large) pentru pozele din PT (#PW și grid).

### 1.2 `object-fit: contain` vs. `cover`

- **home_v2.css (~397):** `body.page-home-v2 #home-col-left .slot-img-fit`, `#home-col-right .slot-img-fit` au `object-fit: contain !important` (sloturi A5/A6, nu A2).
- **style.css (~1650):** un selector pentru bandă/burtieră cu `object-fit: contain`.
- **pet-images-common.css** și regulile pentru A2/P2/fișa câinelui cer explicit `cover`. Nu există conflict direct pe A2 (A2 nu folosește `img`), dar în proiect coexistă `contain` (sloturi laterale, burtieră) și `cover` (câini).

### 1.3 `max-width` / `max-height` pe imagini câini

- **style.css:** `img { max-width: 100% }`; pe anumite layout-uri vechi `img.attachment-pet_single_large` cu `max-width: 275px` / `max-height: 275px` (ex. ~3741, 5016).
- **pet-images-common.css:** pentru A2 `.A2-slot-link` are `max-width: none !important; max-height: none !important`; pentru P2 `.pt-p2-20bg` la fel.
- **style.css (~2659, 3377):** `#all_pets_wrap.pets-grid img.attachment-pet_single_large` are `max-width: none !important` (și fără max-height restrictiv în blocul 3374). Pe gridul PT și pe A2/P2, regulile cu `max-width: none` (și cele din pet-images-common) au prioritate față de regulile generice sau vechi cu max-width/max-height limitate.

### 1.4 Transform / scale la hover

- **style.css (~1554):** `.single_pet:hover img { transform: scale(10); opacity: 0; }` – pentru vechiul bloc .single_pet (nu folosit în A2).
- **style.css (~3465):** `#all_pets_wrap.pets-grid .pet-card-img-wrap:hover .attachment-pet_single_large { transform: scale(1.04); }` – **hover zoom pe cardurile din lista de animale (PT).**
- **pet-images-common.css (~28–30):** `body.page-home-v2 #A2 .A2-slot .A2-slot-link:hover { transform: none !important; }` – anulează orice zoom pe A2. Pe A2 nu există zoom la hover (câștigă pet-images-common). Pe lista PT, zoom-ul de 1.04 rămâne activ.

---

## 2. Ce selector câștigă pentru A2 (HOME)

- **Container slot:** `body.page-home-v2 #A2 .A2-slot` – **Câștigă:** **pet-images-common.css** – `overflow: hidden !important` (și home_v2.css dă position, width, height, background, dar overflow e suprascris de common).
- **Elementul cu imaginea (link cu background-image):** `body.page-home-v2 #A2 .A2-slot .A2-slot-link` / `body.page-home-v2 #A2 .A2-slot a.A2-slot-link` – **Câștigă:** **pet-images-common.css** – toate proprietățile relevante pentru imagine sunt cu `!important` și fișierul vine după home_v2.css: `position: absolute; inset: 0; display: block; width: 100%; height: 100%; background-size: cover; background-position: center center; background-repeat: no-repeat; max-width: none; max-height: none; transform: none`. La **:hover**, tot **pet-images-common.css** – `transform: none !important` pe `.A2-slot-link:hover`.

Pe A2 nu există `img`; imaginea este doar pe link prin `background-image` (inline în home_v2.html). Regulile din style.css pentru `img` nu se aplică conținutului A2.

---

## 3. Ce selector câștigă pentru pagina câinelui (pets-single, fișa câinelui)

- **Container slot:** `.pet-fisa-slot` – **Câștigă:** **pet-images-common.css** – `overflow: hidden !important`. În **pets-single.html** există și stiluri inline pentru `.pet-fisa-slot` (aspect-ratio, background etc.), dar fără `!important`, deci overflow vine din common.
- **Imaginea din slot (cele 3 poze):** `.pet-fisa-slot img` – **Câștigă:** **pet-images-common.css** – toate cu `!important`: `width: 100%; height: 100%; object-fit: cover; object-position: center center; display: block`. **pets-single.html** are în `<style>` reguli pentru `.pet-fisa-slot img` (width, height, object-fit, display) fără `!important`, deci sunt suprascrise de pet-images-common. **style.css** `img { max-width: 100%; height: auto }` se aplică în continuare la nivel de element, dar pentru .pet-fisa-slot img, width/height/object-fit din pet-images-common (cu !important) stabilesc cum umple slotul; max-width: 100% nu schimbă comportamentul de „umplere” în acest context.

Rezumat: pe fișa câinelui, pentru cele 3 poze din `.pet-fisa-slot`, **selectorul care câștigă** este **`.pet-fisa-slot img`** din **pet-images-common.css**.

---

## 4. Unde este definit hover zoom-ul

- **Lista de animale (Prietenul tău – grid carduri):** **style.css, linia 3465–3466:** `#all_pets_wrap.pets-grid .pet-card-img-wrap:hover .attachment-pet_single_large { transform: scale(1.04); }` – aici este definit **hover zoom-ul** pentru imaginile din cardurile de pe pagina „Prietenul tău” (clasa `.attachment-pet_single_large` în `.pet-card-img-wrap`). În același fișier, ~3462–3464: `.pet-card-img-wrap .attachment-pet_single_large { transition: transform 0.25s ease; }`.

- **A2 (HOME):** Nu există hover zoom. **pet-images-common.css (l. 28–30)** forțează `transform: none !important` pe `body.page-home-v2 #A2 .A2-slot .A2-slot-link:hover` (și pe `a.A2-slot-link:hover`), deci orice regulă care ar pune scale pe link este anulată.

- **Alte hover zoom / scale (nu pentru pozele câinilor din A2/PT/fișă):** **style.css ~1554:** `.single_pet:hover img { transform: scale(10); }` – vechi, pentru .single_pet. **style.css ~5927:** `.sidebar-box:hover .sidebar-box-image img { transform: scale(1.05); }` – sidebar. **pets-single.html inline:** `.back-to-friends-btn:hover { transform: scale(1.05); }` – buton, nu imagine câine.

---

## Rezumat pe categorii

| Proprietate / efect | Unde apare | Conflict / câștigător |
|---------------------|------------|-------------------------|
| **background-size** | A2: pet-images-common (cover). P2: pet-images-common (cover). Navbar/fancybox (contain) – alte zone. | Pe A2/P2 câștigă pet-images-common. |
| **img** generic | style.css: max-width 100%, height auto. | Suprascris de reguli specifice (#PW img, .pets-grid img, .pet-fisa-slot img) cu width/height 100%, object-fit cover, eventual max-width none. |
| **object-fit** | cover în pet-images-common, home_v2, pt-v2, style (grid); contain în home_v2 (slot-img-fit), style (burtieră). | Pe imagini câini (A2 link, P2 bg, fișă .pet-fisa-slot img, grid .attachment-pet_single_large) câștigă cover. |
| **transform scale** | style: .single_pet:hover img scale(10); .pet-card-img-wrap:hover .attachment-pet_single_large scale(1.04); pet-images-common: A2-slot-link și :hover transform none. | A2: câștigă transform none (pet-images-common). Lista PT: rămâne scale(1.04) (style.css). |
| **max-width / max-height** | style: img max-width 100%; unele .attachment-pet_single_large cu max 275px. pet-images-common și style: max-width none pe A2 link, P2 bg, pets-grid img. | Pe A2, P2 și grid PT câștigă regulile cu max-width none / !important. |

---

*Document generat pentru export – audit sistem imagini CSS.*
