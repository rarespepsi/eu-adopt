# Poze A2 – Diagnostic și crop la upload

**Scop:** Notă că problema rămasă la unele poze în A2 vine din **fișierul imaginii**, nu din layout-ul A2. Soluția corectă pentru viitor este **crop manual la upload** (deja implementat); acest document descrie unde e și cum funcționează.

---

## 1. Diagnostic: problema nu este în A2

**Decizie (martie 2026):** Nu se mai modifică A2 global.

Pozele care în A2 par cu spații albe, tăiate ciudat sau „prea mici” au de obicei una dintre cauze în **fișierul sursă**:

- **Margini albe** – imaginea încărcată conține deja borduri albe.
- **Subiect prea mic** – câinele ocupă o zonă mică din cadru; canvas-ul e mare.
- **Canvas prea mare** – raportul de aspect sau dimensiunile fișierului nu se potrivesc cu caseta 4:3.
- **Încadrare slabă** – poziția subiectului în imagine nu e potrivită pentru afișare în casetă.

**Concluzie:** Dacă verifici o poză-problemă și constați margini albe / subiect mic / canvas mare / încadrare slabă → **problema este în fișierul imaginii**, nu în layoutul A2. Layoutul A2 (CSS, sloturi, background-size: cover) este corect.

---

## 2. Soluția corectă: crop manual la upload

Soluția pentru viitor este **sistemul de crop manual la upload**: utilizatorul poate **trage (drag)** și **mări/micșora (zoom)** imaginea în previzualizare, apoi la salvare **poziția și zoom-ul sunt trimise** și imaginea este **croapată la raport 4:3** (landscape, ca A2/P2) înainte de a fi salvată.

### 2.1 Ce există deja

| Componentă | Locație | Descriere |
|------------|---------|-----------|
| **Previzualizare + drag + zoom** | `templates/anunturi/cont-adauga-animal.html` | 3 preview boxes (267×200 px); JS: drag (mouse), zoom (wheel); la submit se completează câmpurile ascunse. |
| **Câmpuri ascunse** | Același template | Per poză: `imagine_1_scale`, `imagine_1_cx`, `imagine_1_cy`, `imagine_1_iw`, `imagine_1_ih` (idem 2, 3). Scale = zoom; cx, cy = offset drag; iw, ih = dimensiuni naturale imagine. |
| **Backend crop** | `anunturi/views.py` | `_apply_caseta_crop_to_request(request, box_w=267, box_h=200)` citește scale, cx, cy, iw, ih din POST; pentru fiecare poză nouă apelează `_crop_upload_to_caseta()`. |
| **Crop la 4:3** | `anunturi/views.py` | `_crop_upload_to_caseta()`: din fișierul uploadat + pan/zoom calculează regiunea vizibilă, extrage un dreptunghi 4:3, redimensionează la 800×600, salvează JPEG; returnează `SimpleUploadedFile` care înlocuiește fișierul din `request.FILES`. |
| **Salvare** | `cont_adauga_animal_view` | Înainte de `PetAdaugaForm(request.POST, files)` se apelează `files = _apply_caseta_crop_to_request(request)`. Formularul primește deja imaginile croapate. |
| **După salvare** | `anunturi/models.py` – `Pet.save()` | `_ensure_landscape_image()`: dacă imaginea e deja ~4:3, o lasă neschimbată; altfel o pune pe canvas 1200×900 cu letterbox. |

Rezultat: la **adăugare animal nou**, dacă utilizatorul folosește drag/zoom în preview și imaginea are `iw`/`ih` setate (la load), fișierul salvat este deja croapat 800×600 (4:3) și se afișează corect în A2 și P2.

### 2.2 De ce unele poze rămân „problema”

- **Animale adăugate înainte** de implementarea crop-ului – fișierul salvat nu a trecut prin crop; poate avea letterbox (canvas 1200×900) sau raport nepotrivit.
- **Fără interacțiune** cu preview – dacă utilizatorul nu dă zoom/drag, se trimit scale=1, cx=0, cy=0; crop-ul se aplică dar pe „tot cadrul”, deci dacă sursa are margini albe, ele rămân.
- **iw/ih = 0** – dacă pentru un motiv (ex. imagine neîncărcată în preview) `imagine_X_iw` sau `imagine_X_ih` sunt 0, `_apply_caseta_crop_to_request` nu aplică crop pentru acea poză și se folosește fișierul original.

### 2.3 Îmbunătățiri posibile (viitor)

- **UX:** Text scurt lângă preview: „Poți trage și mări/micșora imaginea pentru a o încadra în casetă.”
- **Edit animal:** La editarea unui animal existent, perioada de re-upload cu același flux (preview + drag/zoom + crop) permite „re-crop” pentru poze-problemă.
- **Poze existente:** Pentru animale deja salvate cu poze slabe: fie re-upload (utilizator) fie, la nevoie, un script one-off care detectează imagini cu aspect != 4:3 sau cu zone albe și oferă re-procesare (opțional).

---

## 3. Reguli de lucru

- **Nu se modifică A2 global** pentru a „repara” anumite poze; problema este în sursă.
- La raportare de poze care „nu umplu caseta”: verifică dacă fișierul sursă are margini albe, subiect mic, canvas mare sau încadrare slabă → notează că **cauza este fișierul**, nu layoutul.
- Pentru poze noi: **crop manual la upload** (drag + zoom + salvare poziție) este soluția corectă și este deja implementată; la nevoie se îmbunătățește UX-ul sau se expune și la edit.

---

*Referință tehnică – martie 2026.*
