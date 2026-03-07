# ⚠️ FIȘIER VECHI – CONȚINUT CENTRALIZAT

**📚 Acest fișier a fost centralizat în `DOCUMENTATIE_CENTRALIZATA.md`**  
**Nu mai actualiza acest fișier – folosește fișierul centralizat pentru a evita duplicarea informațiilor.**

---

# Setări Logo - Documentație

## Configurație Generală Logo

### Dimensiuni Standard
- Container logo: 320px x 320px
- Imagine logo: 229px x 229px
- Stele: 260px x 260px (cerc)
- Fundal circular alb: raza 114.5px

### Stele
- 12 stele alternând galben (#FFD700) și albastru (#003399)
- Formă: 5 vârfuri
- Distribuție: uniformă pe cerc, raza 104px (viewBox 300x300)
- Poziționare: centrat pe logo

### Stiluri Generale
- `border-radius: 50%` pentru formă circulară
- `background-color: #FFFFFF` pentru fundal alb
- `box-shadow: 0 2px 8px rgba(0,0,0,0.15)` pentru umbrire
- `object-fit: contain` pentru imaginea logo-ului

---

## Pagina Home

### Poziție Logo
- `left: -360px` (10cm la stânga de marginea containerului)
- `top: 184px`
- `position: absolute`
- `z-index: 10`

### Identificare Provizorie
- ~~Text: "1home" (roșu, centrat pe logo)~~ **ELIMINAT**
- Clasă body: `page-home`

### CSS Selector
```css
body.page-home .the_logo_link:not(.the_logo_link_contact):not(.the_logo_link_contact_left)::after
```

---

## Pagina Animale (pets-all.html)

### Poziție Logo
- Similar cu pagina home (verifică CSS pentru `.the_logo_link`)

### Identificare Provizorie
- ~~Text: "1animale" (roșu, centrat pe logo)~~ **ELIMINAT**
- Clasă body: `page-animale`

### CSS Selector
```css
body.page-animale .the_logo_link:not(.the_logo_link_contact):not(.the_logo_link_contact_left)::after
```

### Observații
- Logo-ul este inclus în burtiera mică (strip banner) pe partea stângă
- Clasă CSS: `#burtiera_mica .burtiera_logo`

---

## Pagina Contact

### Logo 1 (Din Stânga)
- **Poziție**: `left: 983px` (29 cm de la marginea stângă)
- **Top**: `12px`
- **Clasă**: `.the_logo_link_contact_left`
- **ID**: `#logo_contact_left`
- **Identificare**: ~~Text "2contact" (provizoriu)~~ **ELIMINAT**
- **Stele**: Normal (fără oglindă)

### Logo 2 (Din Dreapta, Oglindit)
- **Poziție**: `right: -567px` (15 cm în afara containerului, pe partea dreaptă)
- **Top**: `12px`
- **Clasă**: `.the_logo_link_contact`
- **ID**: `#logo_contact`
- **Identificare**: ~~Text "1contact" (provizoriu)~~ **ELIMINAT**
- **Transform**: `scaleX(-1)` (oglindă orizontală)
- **Stele**: Oglindite (`transform: translate(-50%, -50%) scaleX(-1)`)

### Observații Pagina Contact
- Logo-ul din header a fost șters din HTML (nu apare)
- Clasă body: `page-contact`
- Container: `#main_content .container` cu `overflow: visible !important`

---

## Texturi Provizorii pentru Identificare

### Stiluri Text Identificare
- Font size: 40px
- Font weight: bold
- Culoare: red (#FF0000)
- Fundal: rgba(255, 255, 255, 0.9)
- Padding: 10px 20px
- Border: 3px solid red
- Border radius: 10px
- Text shadow: 2px 2px 4px rgba(0,0,0,0.5)
- Z-index: 100
- Pointer events: none

### Texturi pe Pagini
- ~~Home: "1home"~~ **ELIMINAT**
- ~~Animale: "1animale"~~ **ELIMINAT**
- ~~Contact Logo 1: "1contact"~~ **ELIMINAT**
- ~~Contact Logo 2: "2contact"~~ **ELIMINAT**

**NOTĂ**: Aceste texturi provizorii au fost eliminate din CSS.

---

## Fișiere Modificate

### Templates HTML
- `templates/anunturi/home.html` - Clasă body `page-home`
- `templates/anunturi/pets-all.html` - Clasă body `page-animale`
- `templates/anunturi/contact.html` - Clasă body `page-contact`, logo din header șters

### CSS
- `static/css/style.css` - Toate stilurile pentru logo-uri și texturi provizorii

---

## Conversie Unități

- 1 cm = 37.795 px (la 96 DPI)
- 3 cm = 113.385 px ≈ 113px
- 10 cm = 377.95 px ≈ 378px
- 15 cm = 566.925 px ≈ 567px
- 29 cm = 1096.055 px ≈ 1096px (dar folosit 983px pentru logo contact left)

---

## Pași pentru Finalizare

1. ✅ **COMPLETAT**: Elimină toate texturile provizorii ("1home", "1animale", "1contact", "2contact")
2. Verifică pozițiile finale ale logo-urilor pe toate paginile
3. Asigură-te că logo-urile sunt corect poziționate și vizibile
4. Testează pe diferite rezoluții de ecran
5. Elimină acest fișier de documentație dacă nu mai este necesar

---

*Document creat pentru referință în timpul dezvoltării. Setările pot fi modificate în funcție de nevoile finale.*
