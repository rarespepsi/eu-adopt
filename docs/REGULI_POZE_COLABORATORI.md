# Reguli pentru pozele încărcate de colaboratori

*Document de referință: ce fel de fișiere, dimensiuni și format trebuie să respecte pozele trimise de colaboratori (animale, profil, etc.).*

---

## Formate acceptate (tip fișier)

- **Recomandat:** **JPEG (.jpg, .jpeg)** – pentru fotografiile de animale și profil; bun raport calitate/dimensiune.
- **Acceptat:** **PNG (.png)** – pentru logo-uri, sigle sau imagini cu transparență.
- **Acceptat:** **WebP (.webp)** – dacă este suportat de formulare/backend; bun pentru web și mobil.

**Nu se acceptă:** fișiere foarte mari (RAW), BMP, TIFF pentru upload obișnuit (dacă nu există procesare specială).

---

## Dimensiuni recomandate (în pixeli)

| Utilizare | Lățime recomandată | Înălțime recomandată | Observații |
|-----------|--------------------|----------------------|------------|
| **Poză animal (principală)** | 800–1200 px | 600–900 px | Raport ~4:3 sau 3:2; site-ul afișează responsive cu `max-width: 100%`, `object-fit: cover`. |
| **Poză 2 / Poză 3 (animal)** | 800–1200 px | 600–900 px | Același raport ca poza principală. |
| **Poză profil utilizator/ONG** | 400–800 px | 400–800 px | Pătrat sau aproape pătrat (ex. 600×600). |
| **Poze post-adopție** | 800–1200 px | 600–900 px | La fel ca pozele animal. |

**Important:** Pozele mai mari se redimensionează în browser (CSS). Pentru **mobil** nu e nevoie de fișiere „speciale”; orice poză cu `max-width: 100%` și `object-fit: cover` se adaptează. Dimensiunile de mai sus asigură calitate bună fără fișiere inutil de mari.

---

## Dimensiune maximă fișier (pe fișier)

- **Recomandat:** **max 2–3 MB** per poză.
- **Acceptabil în practică:** până la **5 MB** dacă serverul și formularele permit; peste 5 MB se dezincurajează (încărcare lentă pe mobil).

Dacă în backend există validare (`max_upload_size`), această valoare trebuie aliniată la regulile de mai sus.

---

## Calitate și aspect

- **Rezoluție:** minim **800 px** pe latura lungă pentru pozele de animale, ca pe mobil (zoom, ecran mic) să rămână clare.
- **Aspect:** preferabil **orizontal** (landscape) sau **pătrat** pentru poza principală animal; evitați foarte înguste sau foarte înalte (ex. 400×2000).
- **Conținut:** imagine clară, animal vizibil; fără date personale sau texte sensibile în poză.

---

## Rezumat rapid (pentru colaboratori)

1. **Format:** JPG (sau PNG dacă e nevoie de transparență).
2. **Mărime fișier:** sub 3 MB per poză.
3. **Dimensiuni:** 800–1200 px lățime, 600–900 px înălțime (sau pătrat 600×600 pentru profil).
4. **Mobil:** nu e nevoie de poze separate; site-ul le afișează adaptat. Încărcați o singură poză de calitate rezonabilă.

---

*La modificări la formulare de upload sau validări în backend, folosiți aceste reguli ca referință. Regulă Cursor: `.cursor/rules/poze-colaboratori.mdc`.*
