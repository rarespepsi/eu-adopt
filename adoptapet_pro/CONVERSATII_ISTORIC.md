# ⚠️ FIȘIER VECHI – CONȚINUT CENTRALIZAT

**📚 Acest fișier a fost centralizat în `DOCUMENTATIE_CENTRALIZATA.md`**  
**Nu mai actualiza acest fișier – folosește fișierul centralizat pentru a evita duplicarea informațiilor.**

---

# Istoric conversații / Lucrări făcute în proiect

Acest fișier rezumă ce s-a discutat și implementat în sesiunile de lucru (conversațiile din Cursor nu se salvează automat; acest document servește ca referință).

---

## 1. Logo și stele

- **Stele**: 12 stele pe cerc, alternând galben (#FFD700) și albastru (#003399), formă cu 5 vârfuri.
- **Dimensiuni**: container 320px, imagine logo 229px, stele 260px.
- **SVG complet**: salvat în `static/images/eu-adopt-logo-complete.svg` (variantă cu stele + referință la imagine).

---

## 2. Pagina Home

- Logo poziționat: `left: -360px`, `top: 184px`.
- Text provizoriu pe logo: **"1home"** (pentru identificare).
- Body cu clasa: `page-home`.

---

## 3. Pagina Animale (Toate animalele)

- Burtieră mică (strip) cu logo în stânga, în loc de slider mare.
- Logo cu text provizoriu: **"1animale"**.
- Body cu clasa: `page-animale`.
- View `pets_all` trimite `strip_pets` pentru burtieră.

---

## 4. Pagina Contact

- **Fără logo în header** – logo-ul din header a fost șters din HTML pe această pagină.
- **Două logo-uri în conținut**:
  - **Logo 1 (stânga)**: `left: 983px`, text **"2contact"**.
  - **Logo 2 (dreapta, oglindit)**: `right: -567px`, text **"1contact"**, `transform: scaleX(-1)`.
- Body: `page-contact`.
- Container cu `overflow: visible` ca să se vadă logo-urile.

---

## 5. Texturi provizorii pe logo-uri

- **1home** – pagina Home.  
- **1animale** – pagina Animale.  
- **1contact** – logo din dreapta pe Contact.  
- **2contact** – logo din stânga pe Contact.  

Scop: identificare ușoară. La finalizare se elimină aceste texturi (și regulile CSS corespunzătoare).

---

## 6. Schema site (casute și spații)

- **Rută**: `/schema-site/` (template: `templates/anunturi/schema-site.html`).
- **Conținut**: schelet vizual al paginilor, fără poze/logo, doar:
  - casute numerotate pentru postări (câini);
  - spații pentru reclame;
  - banner/burtiere.
- **Layout-uri reflectate**:
  - **Home**: 2×2 (4 casute).
  - **Animale**: 2×7 (2 linii × 7 coloane = 14 casute).
  - **Contact**: conținut + sidebar reclame.
  - **Detalii animal**: detalii + formulare + sidebar.

---

## 7. Fișiere importante modificate/create

| Fișier | Modificări / Rol |
|--------|-------------------|
| `static/css/style.css` | Toate stilurile logo (inclusiv Contact), stele, texturi provizorii, grid-uri. |
| `templates/anunturi/contact.html` | Logo șters din header; două logo-uri în conținut. |
| `templates/anunturi/home.html` | Clasă `page-home`. |
| `templates/anunturi/pets-all.html` | Burtieră mică, clasă `page-animale`. |
| `templates/anunturi/schema-site.html` | Pagina de schemă (casute + reclame). |
| `anunturi/views.py` | `pets_all` cu `strip_pets`; view pentru schema. |
| `anunturi/urls.py` | Rută `schema-site/`. |
| `SETARI_LOGO.md` | Documentație setări logo. |
| `static/images/eu-adopt-logo-complete.svg` | Logo complet (stele + referință imagine). |

---

## 8. Pași pentru finalizare (când e cazul)

1. Eliminare texturi provizorii: "1home", "1animale", "1contact", "2contact" (din CSS și/sau template-uri).
2. Verificare poziții logo pe toate paginile și pe diferite rezoluții.
3. Decizie: păstrare sau eliminare fișier `CONVERSATII_ISTORIC.md` și `SETARI_LOGO.md` după ce nu mai sunt necesare.

---

## Notă

Conversațiile din Cursor nu sunt salvate în proiect; acest document este un rezumat făcut după lucrări. Pentru detalii tehnice despre logo (poziții, culori, clase), vezi **SETARI_LOGO.md**.
