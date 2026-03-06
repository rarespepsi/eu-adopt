# ⚠️ FIȘIER VECHI – CONȚINUT CENTRALIZAT

**📚 Acest fișier a fost centralizat în `DOCUMENTATIE_CENTRALIZATA.md`**  
**Nu mai actualiza acest fișier – folosește fișierul centralizat pentru a evita duplicarea informațiilor.**

---

# Modificări EU Adopt – istoric pentru backup

**Scop:** Toate modificările făcute la proiect sunt notate aici. Când site-ul merge, actualizează acest fișier și fă backup (commit + push).

---

## Cum folosești acest fișier

- **După ce faci o modificare** → adaugi o intrare mai jos (dată, fișier, ce s-a schimbat).
- **Când site-ul merge bine** → salvezi setările: verifici BACKUP_GENERAL.md și SETARI_BACKUP.md, faci commit și push. Astfel ai un punct de recuperare.

---

## Modificări notate

### 1. Stabilizare burtieră / slider pagină principală (feb. 2026)

**Fișier:** `static/css/style.css`

**Motiv:** Burtiera (banda de poze de sus) nu avea poziție stabilă; după ce s-a scos/comportamentul s-a schimbat, pozele mișcau layout-ul.

**Ce s-a schimbat:**

1. **#slider_wrap**
   - Înainte: `height: auto;`
   - După: `width: 100%; min-height: 280px; aspect-ratio: 2880/1000; overflow: hidden;`
   - Efect: Zona slider-ului are înălțime rezervată și proporții stabile (ca imaginile 2880×1000).

2. **Container FlexSlider**
   - Adăugat: `#slider_wrap .flexslider` și `#slider_wrap .flex-viewport` cu `height: 100% !important; min-height: 280px;`

3. **Slide-uri**
   - `#slider_wrap .slides`: `height: 100% !important; min-height: 280px;`
   - `#slider_wrap .slide_image_wrap`: `height: 100%;`
   - `ul.slides`: din `height: 260px` în `min-height: 280px; height: 100%;`

4. **Imagini în slider**
   - `#slider_wrap img`: `width: 100%; height: 100%; display: block; object-fit: cover;` (în loc de `height: auto`).
   - Efect: Pozele umplu banda fără să deformeze și fără să miște layout-ul.

5. **Skeleton (show-skeleton)**
   - `body.show-skeleton #slider_wrap` și slide-urile: `min-height: 260px` → `280px` pentru consistență.

**Dacă trebuie refăcut:** Caută în `style.css` secțiunea „=== Slider Area” și „ul.slides” și aplică regulile de mai sus.

---

### 2. Alte fișiere modificate (conform git status, înainte de această sesiune)

- `anunturi/views.py` – modificat (conținut ne-notat aici; verifică cu `git diff` dacă ai nevoie de detalii).
- `templates/anunturi/contact.html` – modificat.
- `templates/anunturi/pets-all.html` – modificat.

*Poți rula `git diff adoptapet_pro/anunturi/views.py` (sau path relativ din repo) pentru a vedea exact ce s-a schimbat.*

---

## Checklist când site-ul merge – backup setări

- [ ] Site-ul se încarcă: eu-adopt.ro și eu-adopt.onrender.com
- [ ] Admin merge: /admin/
- [ ] Animalele apar pe prima pagină și pe Animale
- [ ] Formularul de contact funcționează (dacă e cazul)
- [ ] Actualizat BACKUP_GENERAL.md dacă ai schimbat link-uri / comenzi
- [ ] Actualizat SETARI_BACKUP.md dacă ai schimbat Build/Start/Environment pe Render
- [ ] Adăugat în MODIFICARI.md orice modificare nouă
- [ ] Commit + push pe GitHub (mesaj clar, ex: „Backup setări feb 2026 – slider stabil”)

---

*Creat feb. 2026. Păstrează acest fișier în proiect și actualizează-l când faci modificări sau când site-ul merge și vrei să salvezi starea.*
