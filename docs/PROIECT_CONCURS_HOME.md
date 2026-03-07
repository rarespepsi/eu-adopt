# Proiect: Concurs Home

*Document de planificare și specificații pentru funcționalitatea "Concurs Distribuiri" în caseta A7.*

---

## Rezumat cerințe

### 1. Ce înseamnă "distribuire"
- Membru **partajează o postare cu câine** de pe site pe **propriile pagini de rețele sociale** (Facebook, Instagram etc.)
- Contorizăm **click pe butonul de share** (nu putem verifica dacă postarea a fost efectiv publicată)

### 2. Cine intră în clasament
- **Doar utilizatori înregistrați** (cont pe site)
- **Vizitatori neînregistrați:** dacă dau click pe **caseta cu premiul** → redirect la **înregistrare** (sau login + "Nu ai cont? Înregistrează-te")

### 3. Conținutul despre premiu (în casetă)
- **Depinde de fiecare concurs** (configurabil per ediție)
- Poate fi: **un scurt video** sau **2–3 imagini** (ex: producător, sponsor, produs)
- **Afișare:** imaginile premiului, **una după alta**, la **3–4 secunde** (slideshow)

### 4. Structura casetei A7
- **Sus:** mic link clickabil → **Clasament complet** (pagină cu toată lista)
- **Mijloc:**
  - **Slideshow** cu imaginile (sau video) premiului (3–4 s între imagini)
  - **Clasament** în casetă: doar **primele 5 sau 10 poziții** (alocate în funcție de spațiul din A7)
  - Cele două (premiu vs clasament) se **alternează** în timp (ex: 10–15 s per panou)
- **Jos:** mic link clickabil → **Regulamentul concursului** (pagină sau PDF)

### 5. Clasamentul
- **Generat 100% automat** din datele site-ului (număr de distriburi per user)
- **Fără nimic manual:** nici imagini cu clasament, nici liste introduse de mână
- În A7: **primele 5 sau 10** din baza de date (în funcție de spațiu)
- Pe pagina de clasament: **lista întreagă**, tot din baza de date

---

## Ce trebuie implementat

### A. Contorizare distriburi
- La click pe share (user logat) → înregistrare 1 distribuire (user + postare, eventual și data)
- Model/câmpuri pentru: user, (opțional) postare, (opțional) data
- Agregare pentru "număr total distriburi per user"

### B. Configurare concurs
- Per ediție: video sau 2–3 imagini premiu
- Link regulament
- Perioadă concurs (start/end date)
- **IMPORTANT:** Nu se dă drumul automat fără OK explicit

### C. A7 – Componentă
- Bloc reutilizabil cu:
  - Link sus (clasament complet)
  - Slideshow premiu + panou clasament top 5–10 (alternate)
  - Link jos (regulament)
- Click pe premiu (neînregistrat) → redirect înregistrare

### D. Pagină clasament complet
- Listă generată din aceleași date, sortată după număr distriburi
- Toate pozițiile, nu doar top 5–10

### E. Monitor pe laptop (viitor)
- Preview A6–A11 (doar casetele de reclamă/publicitate)
- Setări: durată, perioadă, ore de difuzare
- Încărcare video producător
- Enter pentru aplicare
- **De decis:** Variantă A (pagină web pe site) sau B (app separată pe laptop)

---

## Structură tehnică propusă

### Modele Django
- `Share` (user, pet_post, timestamp)
- `Contest` (title, start_date, end_date, is_active, rules_url, prize_video, prize_images[])
- `ContestPrizeImage` (contest, image, order, label)

### Views
- `share_pet_post()` – endpoint pentru click share
- `contest_leaderboard()` – clasament complet
- `contest_leaderboard_widget()` – top 5–10 pentru A7

### Templates
- `components/contest_widget.html` – componentă A7
- `contest/leaderboard.html` – pagină clasament complet

### Static/Media
- Folder pentru media concurs: `media/contests/` sau `static/contests/`

---

## Checkpoint "x home"

**IMPORTANT:** Înainte de implementare, facem checkpoint al setărilor "x home" pentru rollback dacă nu iese.

Setări memorate în: `HOME_SETTINGS_REFERENCE.md` (secțiunea "Salvarea x home")

---

## Status

- [ ] Checkpoint "x home" creat
- [ ] Model Share creat
- [ ] Model Contest creat
- [ ] Endpoint share_pet_post implementat
- [ ] Componentă A7 (contest_widget) creată
- [ ] Pagină clasament complet creată
- [ ] Admin pentru configurare concurs
- [ ] Testare contorizare distriburi
- [ ] Testare alternare premiu/clasament în A7
- [ ] Monitor laptop (viitor)

---

*Document creat pentru referință viitoare. Nu se implementează acum – așteptăm finalizarea altor pagini.*
