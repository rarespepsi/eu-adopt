# Arhivă – Idei, taskuri amânate și propuneri

**Trecere în revistă a proiectului:** tot ce s-a spus să reținem, să facem altă dată, idei sau propuneri nepus încă în practică. Arhivat pentru referință la finalizarea site-ului.

*Creat: februarie 2026*

---

## Rezumat sesiune – 22 februarie 2026

1. **Pagina Beneficii după adopție** – Dacă userul nu are nicio adopție finalizată, vede doar pagina de informare cu textul „Beneficiile sunt disponibile doar după finalizarea unei adopții.” și butonul „Vezi animalele”. Pagina completă cu cupoane se afișează doar când are cel puțin o cerere finalizată.

2. **Mesaj când userul are deja o cerere** – Pe fișa câinelui și pe butoane: în loc de „Cerere trimisă (poziția X)” se afișează „Ai deja o cerere pentru acest câine: [status]” (ex. În așteptare, Aprobată, Finalizată), plus poziția în coadă unde e cazul.

3. **Badge câine rezervat** – Textul badge-ului pentru câini rezervați a fost schimbat din „În curs de adopție” în „REZERVAT / În curs” (pe pagina animalului și pe cardurile din listă).

4. **Status și câmpuri noi la cererea de adopție (AdoptionRequest)** – Adăugat status NO_SHOW („Nu s-a prezentat”); actualizate etichete (PENDING, APPROVED, REJECTED, CANCELLED, FINALIZED); adăugate câmpuri: approved_at, finalized_at, cancelled_at, finalized_by (FK către User = adăpostul care finalizează).

5. **Migrație** – Creată și aplicată migrația 0042_adoption_request_timestamps_finalized_by.

6. **Comportament timestamp-uri** – La aprobare se setează approved_at; la „Adopție finalizată” se setează finalized_at și finalized_by; la anulare rezervare se setează cancelled_at.

7. **Admin** – În admin la cereri adopție: list_display și readonly pentru approved_at, finalized_at, cancelled_at, finalized_by.

---

## Poze A2 – diagnostic și crop (martie 2026)

- **Problema rămasă** la unele poze în A2 nu este în layoutul A2, ci în **fișierul imaginii**: margini albe, subiect prea mic, canvas prea mare, încadrare slabă. Nu se modifică A2 global.
- **Soluția corectă pentru viitor:** sistem de **crop manual la upload** (drag + zoom + salvare poziție). Este deja implementat: preview cu drag/zoom în formularul „Adaugă animal”, câmpuri ascunse (scale, cx, cy, iw, ih), backend `_apply_caseta_crop_to_request` + `_crop_upload_to_caseta` (ieșire 800×600, 4:3). Referință detaliată: **`docs/POZE_A2_SI_CROP_REFERINTA.md`**.

---

## 1. Din conversații recente (de reținut / făcut altă dată)

### Taskuri memorate
| # | Ce | Când |
|---|-----|------|
| 1 | **Reset date la lansare** – ștergere users, câini (animale) și alte date fictive adăugate pentru probe. Opțiuni: Django Admin sau management command (ex. `clear_test_data`). | Când site-ul e gata de lansare. |
| 2 | **Setare acces pe roluri** – Administrator = toate paginile și datele; user de rând (PF, ONG) = acces doar la anumite pagini (restul ascunse în meniu și protejate la view). | Dacă e nevoie; nu acum. |
| 3 | **Modificare navbar pentru mobil** – Adaptare A0 pentru ecrane mici (padding 7cm/6cm → px/em, meniu compact sau hamburger, fără scroll orizontal). | Când ajungem la **finalul construcției paginii home**. |

### Idei nepus în practică
- Afișare **username în navbar** pentru user logat (ex. „Bun venit, {{ user.username }}”) – opțional.
- **Lista de corecturi numerotate** – de stabilit; la „start modificări” se execută în ordine.
- **Traseu** (meniu / rute / flux) – de refăcut sau stabilit la cerere.
- **Caseta sidebar (A6, A7, A8, A9, A10 sau A11)** – colaborare cu cabinetele veterinare din țară care sterilizează gratuit; vizitatorul poate dori să contribuie la cauza sterilizării (informații + eventual donație/contribuție).
- **Pagină Marketing** – afișează doar casetele A6–A11, cu script viitor de postare automată.
- **Pagină Membri / SUPERPOWER** – listă membri + căutare, click → fișa clientului, bifă pentru modificare funcție (rol) și acțiuni (Analiza, Marketing, aprobare anunțuri etc.). Majoritatea membrilor au funcție comună (postare + editare proprii postări).

### Alte amintiri
- **Salvare site** = Git (commit + push); documentele SETARI_* sunt doar referințe scrise, nu înlocuiesc backup-ul.
- **User logat** – în navbar nu se afișează username-ul; doar „Contul meu”, „Logout” (și „Analiza” pentru staff).

---

## 2. Din CONVERSATII_ISTORIC / finalizare

- Eliminare **texturi provizorii** pe logo: "1home", "1animale", "1contact", "2contact" (din CSS și/sau template-uri).
- Verificare **poziții logo** pe toate paginile și pe diferite rezoluții.
- Decizie: păstrare sau eliminare fișiere `CONVERSATII_ISTORIC.md` și `SETARI_LOGO.md` după ce nu mai sunt necesare.

---

## 3. Din WISHLIST.md / DOCUMENTATIE_CENTRALIZATA – funcționalități (făcut la final / viitor)

### Concurs
- **⏳ FĂCEM LA FINAL** – concurs pe site (câștigător = cel cu cele mai multe distribuiri); clasament, premii, secțiune „Top membri”. Nu implementăm acum.

### Pentru promovare
- Link unic per animal, filtre (tip, vârstă, mărime, sex, status), căutare, pagină animal cu dosar clar, SEO.

### Pentru membri
- Conturi per adăpost/asociație; verificare foarte bună (certificat, buletin, telefon, adresă); adresă Google Maps; limită 50 animale/lună; **panou membru** (pe viitor; acum există Django admin); import bulk; raport simplu.

### Alte funcționalități
- **Bandou reclame** – zone pentru reclame producători mâncare, produse animale, veterinar etc.
- **Partajare 1 click** – Facebook, WhatsApp (link pagină animal).
- **Transport** – ofertă transport în altă zonă, comision platformă, **listă transportatori** (național + internațional).
- **Donații** – pagină/secțiune donații, 3,5% impozit (informații + pași).
- **Limbi** – multilingv (ro, en, es, it, de, ru etc.).
- **Calitate** – poze multiple per animal, status vizibil, date medicale obligatorii, validare imagini (script/API), control postări per membru.
- **Tehnic** – performanță (paginare), mobile-friendly, backup/export.

### Prioritizare (din WISHLIST)
- P0: Filtre, link partajabil, juridice puternice (termeni, disclaimer, validare avocat).
- P1: Căutare, poze multiple, locație, facilități, donații, limbi.
- P2: Membri, verificare, Google Maps, date medicale, import, raport.
- P3: Control postări, validare imagini, limită 50 + abonament, transportatori, bandou reclame, concurs, SEO.

---

## 4. Din PROIECT_CONCURS_HOME.md – concurs (viitor)

- **Checkpoint „x home”** înainte de implementare (setări în HOME_SETTINGS_REFERENCE.md).
- Model Share, Contest; endpoint share; componentă A7 (contest_widget); pagină clasament complet; admin concurs.
- **Monitor laptop (viitor)** – preview A6–A11, setări durată/perioadă, încărcare video; de decis: pagină web sau app separată.

---

## 5. Rezumat conversații / referință pentru chat-uri noi

- **`REFERINTA_PROIECT.md`** – rezumat structurat: Făcut, De pus în practică, Decizii, Tehnic. Pentru detalii în chat-uri noi: „Citește REFERINTA_PROIECT.md”. Se actualizează după conversații importante.
- **`.cursor/rules/idei-principale-proiect.mdc`** – lista scurtă de idei principale; se încarcă automat la fiecare conversație nouă (regulă Cursor).

---

## 6. Fișiere sursă (unde mai sunt detaliile)

| Fișier | Conține |
|--------|---------|
| `REFERINTA_PROIECT.md` | Referință proiect – ce e făcut, decizii, unde sunt lucrurile; pentru chat-uri noi. |
| `IDEI_SI_TASKURI_AMANATE.md` | Taskuri și idei amânate – reamintire la finalizare. |
| `WISHLIST.md` | Wish list & viziune site (marcat vechi; conținut parțial în DOCUMENTATIE_CENTRALIZATA). |
| `DOCUMENTATIE_CENTRALIZATA.md` | Documentație centralizată, inclusiv Wishlist & viziune. |
| `PROIECT_CONCURS_HOME.md` | Specificații concurs (A7), structură tehnică, status. |
| `CONVERSATII_ISTORIC.md` | Istoric lucrări (logo, home, animale, contact, schema site, pași finalizare). |
| `MODIFICARI.md` | Istoric modificări (slider, backup setări). |
| `HOME_SETTINGS_REFERENCE.md` | Setări pagină home – referință. |
| `SETARI_LOGO.md` | Setări logo. |
| `AGENDA_PROIECTE.md` | Agenda proiecte, programe, domenii, reminder-uri. |
| `POZE_A2_SI_CROP_REFERINTA.md` | Diagnostic: poze A2 problema = fișier sursă; soluție crop manual la upload (referință tehnică). |

---

## 7. Utilizare

- **Când finalizăm aranjarea paginii / site-ul:** revizuiești acest fișier și `IDEI_SI_TASKURI_AMANATE.md` ca să-ți aduci aminte de taskurile și ideile de făcut.
- **Pentru detalii tehnice** (wish list complet, prioritizare, juridic, transport, etc.): vezi `WISHLIST.md` și `DOCUMENTATIE_CENTRALIZATA.md`.
- **Pentru concurs:** vezi `PROIECT_CONCURS_HOME.md`.

---

*Arhivă consolidată – nu șterge sursele; acest document e index și rezumat.*
