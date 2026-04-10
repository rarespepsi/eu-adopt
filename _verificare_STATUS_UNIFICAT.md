# Status verificări EU-Adopt — unificat (doar acest fișier e adăugat)

**Regulă respectată:** niciun alt fișier din repo nu a fost modificat la crearea acestui document.

**Surse de adevăr (neschimbate):**

- `docs/EU-ADOPT_CARTE_SITE_VERIFICARE.txt` — cartea detaliată a site-ului (puncte numerotate + Apendix O).
- `_verificare_2026-03-31.md` — backlog 30 puncte (secțiuni A–L).

---

## 1. Carte site (`EU-ADOPT_CARTE_SITE_VERIFICARE.txt`) — ce spune repo-ul acum

| Zonă | În fișierul sursă | Notă |
|------|-------------------|------|
| Părți **A–M** (puncte **1–135**) | Toate marcate **`[x]`** | Conform ultimei înregistrări din sursă: ultimul bifat OK **135** (2026-03-29), teste `test_carte_21_135` etc. |
| **Partea N** — matrice rol × zonă | **Fără rânduri `[ ]`/`[x]`** în sursă | **De lucrat manual** (tu pe tabletă + pași de la asistent); sursa notează „Următorul de lucrat: Partea N”. |
| **Apendix O** (puncte **136–247**) | Toate marcate **`[x]`** în sursă | Conform textului din sursă + bife vizibile pe rânduri 136–247. |

**Rezumat:** în cartea din `docs/`, checklist-ul numerotat e bifat; rămâne explicit **Partea N** (QA manual pe roluri).

---

## 2. Backlog `_verificare_2026-03-31.md` — stare checkbox-uri din acel fișier

În `_verificare_2026-03-31.md`, toate punctele sunt încă **`[ ]`** (nebifate acolo). Mai jos e aceeași listă cu **status interpretat** pentru lucru (fără a modifica fișierul sursă).

### A. Legal / pagini publice — *amânat până ai date firmă*

- [ ] Contact — CUI/sediu/telefon (în sursă: task deschis)
- [ ] Termeni — date operator
- [ ] Politici (confidențialitate, cookie, servicii plătite, moderare) — completări adresă/telefon unde e placeholder

**Notă:** nu înseamnă „greșit”; înseamnă **în așteptare** când există entitate + date reale.

### B. Carte & QA

- [ ] **Partea N** — matrice rol × zonă (manual)
- [ ] **Apendix O 136–247** — în sursa carte = deja `[x]`; punctul din backlog = confirmare ta / rulare teste dacă vrei dublură

### C. Pre-lansare (`e2e/PRELAUNCH_CHECKLIST.md`)

- [ ] Verificări manuale (2)
- [ ] Config producție (3)
- [ ] Opțional (4)

### D–L. Restul backlog-ului

- [ ] D — Requests (Analiza), conform `AGENT_FISA_CONTINUITATE.md`
- [ ] E — `home/views.py` (mypet_add, publicitate gateway, shop docstring)
- [ ] F — `DJANGO_LISTA_ADAUGARI.md` (puncte „ce nu e făcut”)
- [ ] G — Cron oferte + Redis multi-worker
- [ ] H — Audit (`analiza-animale.html`, `harta_judete`, `sidebar_box`, `pets-single` galerie)
- [ ] I — `style.css` legacy
- [ ] J — Transport T3 sloturi „rezervat viitor”
- [ ] K — `DOCUMENTATIE_CURATARE.md` §3.4 vs `home/urls.py` (doc depășit față de cod)
- [ ] L — `STIK.txt`, `DEV_MOBIL_LAN.txt` (informative)

---

## 3. Cum lucrăm mai departe (tu verifici, asistentul bifează *unde îmi permiți*)

- **Pe tabletă:** îți dau loturi de pași; tu răspunzi OK / nu merge.
- **În repo:** bifarea în `_verificare_2026-03-31.md` sau în `docs/EU-ADOPT_...txt` necesită **editare fișiere** → doar când îmi spui explicit (ex. „bifează punctul X”) și, conform regulilor proiectului, cu parola **`1977`** dacă e cerută pentru editări.
- **Acest fișier** `_verificare_STATUS_UNIFICAT.md` poate fi **actualizat doar la cererea ta** (sau poți cere o nouă versiune), tot fără a atinge restul dacă vrei regula „nimic altceva”.

---

*Generat: 2026-03-31. Un singur fișier adăugat: `_verificare_STATUS_UNIFICAT.md`.*
