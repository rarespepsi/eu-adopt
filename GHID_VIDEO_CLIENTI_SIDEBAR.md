# Ghid: video de la clienți pentru sloturile sidebar (A6–A8, A9–A11)

Când primești videoclipuri de la clienți pentru casetele din stânga și dreapta, cere-le să respecte cerințele de mai jos. Le poți trimite acest text (sau o variantă scurtă).

---

## Ce să ceri clienților

### Format fișier
- **Format:** MP4 (H.264 video + AAC audio)
- **Alternativ acceptat:** WebM (VP9), MOV (H.264)

### Mărimi / rezoluție
- **Rezoluție recomandată:** 480p sau 720p (suficient pentru casete sidebar)
  - 480p: **854 × 480** pixeli
  - 720p: **1280 × 720** pixeli
- **Raport aspect:** **16:9** (landscape) – se va afișa tăiat uniform în casetă (object-fit: cover)

### Dimensiune fișier și durată
- **Dimensiune:** max. **20–50 MB** per videoclip (pentru încărcare rapidă pe site)
- **Durată:** **15–60 secunde** (ideale pentru promo în sidebar; pot fi și 1–2 min dacă e necesar)

### Conținut
- Fără texte importante în margini (pot fi tăiate pe ecrane înguste).
- Imagine stabilă sau mișcare ușoară – casetele sunt mici, detaliile fine se pierd.

---

## Rezumat pentru email către client

> **Videoclipuri pentru EU Adopt (casete laterale)**  
> - Format: **MP4 (H.264)**  
> - Rezoluție: **854×480** sau **1280×720** (16:9)  
> - Durată: **15–60 sec**  
> - Dimensiune: **max. 50 MB** per fișier  

---

## După ce primești fișierele

- Le poți încărca în **Cloudinary** (sau alt CDN) și vom folosi URL-urile în sloturi.
- Sau le încarci pe **YouTube** (cu „Permite redare pe site-uri externe”) și pui ID-urile în `static/js/home-sidebar-promo.js` în array-ul `YOUTUBE_IDS`.

Dacă vrei și variante pentru reels/stories (verticale), le putem defini separat.
