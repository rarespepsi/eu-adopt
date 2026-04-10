# QA pas cu pas — registru constatări (fără modificări în site în această fază)

**Acord de lucru**

- Verificăm **pas cu pas**; tu pe tabletă / eu îți dau pașii.
- Aici notăm doar **ce e de corectat** sau **comportament suspect** — **nu modificăm cod sau șabloane** până la o rundă separată, cu parolă `1977` când e cazul.
- **„Toate variantele de useri × toate căile”** = parcurgem **sistematic** pe loturi (nu există o listă finită „absolut tot” în sens matematic, dar acoperim **rolurile** și **zonele principale** + linkuri din navbar/footer și căi critice).

**Progres conexiune:** tabletă → `http://<IPv4 PC>:8000` — OK (2026-04-10).

**Tabletă mare:** navbar **orizontal complet** (ca pe desktop), **fără** meniu hamburger — pașii spun „din bara de sus”.

**Utilizatori de test:** vezi **`QA_MATRICE_UTILIZATORI.md`** — **reale (email real):** `rares`, `rarespepsi`, `radu`, `nccristescu`; **demo:** `dpf`, `dg1`, `dg2`, `dm`, `e2e_*`.

---

## 1. Din ce **nu** este verificat (sursă: backlog + carte site)

### A. Prioritate acum — probă manuală (tu + tableta)

*Actualizare produs (cod): lista publică **`/oferte-parteneri/`** a fost **eliminată**; ofertele se văd pe **`/servicii/`**. Verificările COL-P7 / documentația trebuie făcute pe **Servicii**, nu pe URL-ul vechi.*

| ID | Ce | De ce e „neverificat” pentru voi |
|----|-----|-----------------------------------|
| **N1** | **Partea N** — matrice **rol × zonă** | În `EU-ADOPT_CARTE_SITE_VERIFICARE.txt` nu are rânduri `[x]`; e **următorul** după testele automate. |
| **N2** | **Toate tipurile de utilizator** pe **aceleași zone** | Vizitator, PF logat, ONG logat, Colaborator (magazin / servicii / transport), Staff — fiecare trebuie parcurs pe **navbar**, **footer**, **cont**, zone specifice rolului. |
| **N3** | **Căi de legătură** (click din meniu, nu doar URL tastat) | Fiecare buton din A0 care duce undeva; linkuri din footer; unde duce „Înapoi” / login redirect. |
| **N4 / Lot AD** | **Adopție end-to-end** (cerere → accept → bonus Servicii → transport opțional → finalizare) | Matrice proprietar PF/ONG × adoptator PF/ONG privat × cu/fără transport × inimioare 0/1/3 canale — vezi §2bis Lot **AD**. |

### B. Amânat intenționat (date firmă)

| Secțiune | Conținut |
|----------|----------|
| **Backlog A** | Contact, Termeni, politici — placeholder până aveți CUI/sediu/telefon reale. |

### C. Alte puncte din `_verificare_2026-03-31.md` (nu sunt aceeași treabă cu tableta)

| Secțiune | Tip | Notă |
|----------|-----|------|
| **B** — Apendix O 136–247 | În carte e bifat prin teste | Opțional: spot-check manual pe tabletă dacă vreți dublură. |
| **C** | Pre-lansare (prod + config) | După ce terminați matricea manuală. |
| **D–L** | Cod, audit fișiere, cron, doc | Lucru separat (Cursor/agent), nu „click pe site”. |

### D. Fără confuzie: **registrul** vs **Partea N** (carte)

| Unde | Rol |
|------|-----|
| **Acest fișier — §2bis** (V-P1…, PF-P1…, COL-P7…) | Programul **vostru** de verificare pe tabletă — **sursa de adevăr** pentru „ce ați probat deja”. |
| **`docs/EU-ADOPT_CARTE_SITE_VERIFICARE.txt` — Partea N** | Aceeași idee **copiată în documentul „carte site”**. O poți bifa **fără să repeți** toate clickurile: aliniezi cu ce e deja **[x] OK** în §2bis / §2. Nu înseamnă „ia de la capăt”. |
| **§3 mai jos — Registru constatări** | **Lista de probleme** (ce e stricat / de îmbunătățit). **De aici** continuați: remediere, parolă, priorități. |

---

## 2. Roluri de probat (checklist scurt)

Bifează când **ai parcurs** loturile pentru acel rol (bifa = doar în acest registru, manual).

- [x] **V1** — Vizitator (delogat) — Faza V V-P1…V-P10
- [x] **PF** — Persoană fizică (logat) — PF-P1…PF-P4
- [x] **ONG** — `rarespepsi` + `radu` — Cont OK (ONG-P1, ONG-P2)
- [x] **COL-M** — Colaborator magazin — `dm` (COL-P1)
- [x] **COL-T** — Colaborator transport — `rares` + `/collab/transport/` (COL-P2)
- [x] **COL-CAB** — Cabinet veterinar — `nccristescu` (COL-P3, COL-P4 — **MyListVet**)
- [x] **COL-SRV** — Servicii demo — `dg1`, `dg2` (COL-P5, COL-P6)
- [x] **Oferte pe Servicii** — `/servicii/` (COL-P7); lista dedicată `/oferte-parteneri/` **nu mai există** (404)
- [x] **STAFF** — `rares` — Analiză + Reclama + PUB (ST-P1)

*Dacă nu ai un cont pentru un rol, notăm în tabel „lipsă cont test” — nu blocăm restul.*

---

## 2bis. Program verificare **simplificat** (eu spun pasul, tu execuți, eu bifez aici)

**Regulă:** un mesaj = **un singur pas** executat; răspunzi **OK** / **NU** (+ scurt).

### Faza **V** — Vizitator (delogat), din navbar

| Cod | Ce verifici | Status |
|-----|-------------|--------|
| V-P1 | Acasă se încarcă | [x] OK |
| V-P2 | Prietenul tău | [x] OK (încărcare lentă la început, apoi OK) |
| V-P3 | Servicii | [x] OK |
| V-P4 | Transport | [x] OK |
| V-P5 | Shop | [x] OK |
| V-P6 | MyPet → Intră | [x] OK |
| V-P7 | I Love → Intră | [x] OK |
| V-P8 | Termeni și condiții (pagină se încarcă) | [x] OK |
| V-P9 | Contact (formular) | [x] OK |
| V-P10 | Linkuri din subsol pe Acasă (dacă apar) | [x] OK |
| V-P11 | **Nota A1** (click pe logo): delogat — în ghid **nu** apar MyPet, I Love, Publicitate, Magazinul meu; apar Acasă, PT, Servicii, Transport, Shop… | [x] OK |

### Faza **PF** — Logat ca **persoană fizică** (`dpf` sau `e2e_pf`)

| Cod | Ce verifici | Status |
|-----|-------------|--------|
| PF-P1 | După login: navbar diferit (nume, MyPet real, Logout) | [x] OK |
| PF-P2 | MyPet → lista ta (sau goală) | [x] OK — **5 animale** pe contul PF probat |
| PF-P3 | I Love → pagina wishlist | [x] OK |
| PF-P4 | Cont / editează — se deschide | [x] OK |

### Faza **ONG** — Logat (`rarespepsi` sau `radu`)

| Cod | Ce verifici | Status |
|-----|-------------|--------|
| ONG-P1 | Cont — layout organizație OK | [x] OK — user **`rarespepsi`** (**ONG adăpost public**, aliniat `set_org_public` în script) |
| ONG-P2 | Cont — ONG privat | [x] OK — user **`radu`** |

### Faza **COL** — Colaborator (ex. `dm` magazin, `rares` transport)

| Cod | Ce verifici | Status |
|-----|-------------|--------|
| COL-P1 | Magazinul meu / oferte (dacă e tip magazin) | [x] OK — user demo **`dm`** |
| COL-P2 | Panou transport (dacă e tip transport) | [x] OK — user **`rares`** (logare + pagina My transport) |
| COL-P3 | **Cabinet** real **`nccristescu`** — Cont | [x] OK — colaborator **cabinet veterinar** |
| COL-P4 | **Cabinet** `nccristescu` — panou colaborator | [x] OK — pagina **MyListVet**; ~**10 servicii** demo vizibile |
| COL-P5 | **Servicii** demo **`dg1`** — Cont + panou | [x] OK — **My list Servicii**; **10** servicii demo |
| COL-P6 | **Servicii** demo **`dg2`** — Cont + panou | [x] OK — **My list Servicii**; **10** servicii demo |
| COL-P7 | **Servicii** `/servicii/` — oferte parteneri în pagină (carduri / modale); **`/oferte-parteneri/` → 404**; detaliu ofertă rămâne `/oferte-parteneri/<id>/` | [x] OK |

### Faza **ST** — Staff (cont cu drepturi staff)

*Notă:* **`rares`** are și admin — poți folosi același login ca la COL-P2, fără cont separat.

| Cod | Ce verifici | Status |
|-----|-------------|--------|
| ST-P1 | **Analiză**, **Reclama**, **PUB** — în meniu, paginile se deschid | [x] OK — logat **`rares`** (admin) |

*(Completăm fazele pe măsură ce le parcurgem; putem adăuga rânduri noi.)*

### Lot **N3** — Subsol / legături (continuare: **un mesaj = un pas**; agentul bifează la **OK**)

| Cod | Ce verifici | Status |
|-----|-------------|--------|
| N3-P1 | **Delogat** → navbar **Termeni și condiții** → pe hub „Documente legale” click **2) Politica de confidențialitate** → pagina GDPR se încarcă (fără 500) | [x] OK |
| N3-P2 | **Delogat** → din nou hub Termeni (sau înapoi) → **3) Politici complementare** → apoi link **Politica de cookie-uri** → pagina se încarcă | [x] OK |
| N3-P3 | **Delogat**: tot din **3) Politici complementare**, deschide **Politica serviciilor plătite** sau **Politica de moderare** (unul) → se încarcă | [x] OK |

*Lot **N3** — complet (N3-P1…P3).*

### Lot **AD** — Adopție: obiective, matrice, pași (1 laptop + 1 tabletă + 1 telefon)

**Scop:** verificare **reală** a tuturor combinațiilor utile: proprietar (PF / ONG public / ONG privat), adoptator (PF / ONG privat), **inimioare** pe `/servicii/` (0 / parțial / 3 canale), **transport** (cu dispatch + accept / fără / fără transportator în zonă).

**Date DB înainte de probe (o dată pe mediu, după `scripts/_align_user_roles.py`):**

1. `python scripts/qa_adoption_transport_setup.py` — pune **București / București** pe profilurile relevante (adoptatori `dpf`, `e2e_pf`; ONG privat test `radu`; colaboratori `nccristescu`, `dg1`, `dg2`, `dm`; transportator `rares` + **TransportOperatorProfile aprobat** + național).
2. `python scripts/seed_portfolio.py` — animale `[seed]` și oferte `[seed]` (cabinet / servicii / magazin / oferte pe `rares`), dacă lipsesc.
3. **Variantă „fără inimioare magazin” în București:** `python scripts/qa_adoption_transport_setup.py --magazin-remote` (mută doar `dm` în Timiș) — apoi reverifici cu setup-ul normal.

**Reguli din cod (rezumat):**

- Inimioare: adoptatorul are **județ** în `UserProfile` (`judet` sau `company_judet`); oferta colaboratorului folosește **company_judet** sau **judet**; potrivire **casefold** (diacritice consistente).
- Colaboratorul **nu poate fi adoptator**. **ONG adăpost public** nu poate adopta. **Transport:** trebuie **același județ și același oraș** (normalizat) între cerere și profilul transportatorului aprobat.

**Repartizare dispozitive (recomandat):**

| Dispozitiv | Rol tipic în Lot AD |
|------------|---------------------|
| **Laptop** | Proprietar (MyPet: accept / respinge / prelungește / finalizează); poți deschide și e-mail proprietar. |
| **Tabletă** | Adoptator: fișă animal (cerere), `/servicii/` (inimioare), formular transport. |
| **Telefon** | Transportator `rares`: link din e-mail (accept/decline); sau verificare rapidă fișă / PT pe mobil. |

*Dacă ești singur, parcurgi pe rând; ordinea de mai sus reduce schimbul de login.*

---

#### AD — Matrice scenarii (bifează când turul e complet OK)

| ID | Proprietar anunț | Adoptator | Inimioare Servicii (canale) | Transport | Status |
|----|------------------|-----------|-----------------------------|-----------|--------|
| **M1** | PF (`dpf` sau alt PF cu anunț) | Alt PF (`e2e_pf`) | **Fără** (șterge temporar județul adoptatorului în cont / probă fără aliniere) | Fără | [ ] |
| **M2** | PF | PF | **3 canale** (cabinet + servicii + magazin — după `qa_adoption_transport_setup.py` + seed) | Fără | [ ] |
| **M3** | PF | PF | Opțional (0 sau 3) | **Cu** (formular din flux adopție → `rares` acceptă din e-mail) | [ ] |
| **M4** | ONG public `rarespepsi` | PF | Opțional | Fără | [ ] |
| **M5** | ONG public `rarespepsi` | PF | Opțional | Cu | [ ] |
| **M6** | ONG privat `radu` | PF | Opțional | Fără | [ ] |
| **M7** | ONG privat `radu` | PF | Opțional | Cu | [ ] |
| **M8** | PF | ONG privat `radu` (cont separat de proprietarul anunțului) | Opțional | Fără sau cu | [ ] |
| **M9** | Oricare | Oricare | **`--magazin-remote`**: max 2 canale cu inimioare (fără magazin în București) | La alegere | [ ] |

---

#### AD — Pași de execuție (un mesaj în chat = un pas; răspuns **OK** / **NU**)

**Pregătire**

| Cod | Ce verifici / faci | Status |
|-----|-------------------|--------|
| AD-P0 | Ai rulat `qa_adoption_transport_setup.py` (+ `seed_portfolio` dacă trebuie); știi care user e proprietar și care adoptator pentru acest tur. | [ ] |

**Flux adopție (happy path — repetă pentru fiecare rând M1–M9 unde e cazul)**

| Cod | Ce verifici | Dispozitiv sug. | Status |
|-----|-------------|-----------------|--------|
| AD-P1 | Proprietar: animal **publicat**, adopție **deschisă** (MyPet / fișă). | L | [ ] |
| AD-P2 | Adoptator: pe fișă, **cerere adopție** trimisă (`/pets/<id>/adopt/request/`); mesaj corect / stare „în așteptare”. | T | [ ] |
| AD-P3 | Proprietar: în MyPet, vede cererea; **acceptă** (`mypet/adoption/<id>/accept/`). | L | [ ] |
| AD-P4 | Adoptator: pe fișă, mesajele / starea după accept (deblocare mesagerie dacă e cazul). | T | [ ] |
| AD-P5 | Adoptator: deschide **`/servicii/`** — dacă are județ + cerere pending/acceptată: **banner** bonus; ofertele din **același județ** au **inimioară**; click inimioară (max 1 / tip: cabinet / servicii / magazin). | T | [ ] |
| AD-P6 | *Doar dacă turul include transport:* din fișă / flux adopție, ajungi la **Transport** cu `from_adoption=1`; completezi formularul; **județ/oraș** = aceleași ca la `rares` (București după setup). | T | [ ] |
| AD-P7 | *Cu transport:* pe **telefon** sau laptop logat `rares` — e-mail **accept** dispatch (sau panou transportator); cererea intră „asignată”; utilizatorul primește confirmare. | M sau L | [ ] |
| AD-P8 | Adoptator: revenire la fișă cu `?after_transport=1` dacă fluxul o cere — opțiunea transport nu mai blochează incorect. | T | [ ] |
| AD-P9 | Proprietar: **finalizează adopția** (`mypet/adoption/<id>/finalize/`); animal marcat adoptat; adoptator vede starea finală. | L | [ ] |
| AD-P10 | Dacă au fost inimioare selectate: **e-mail** adoptator cu coduri / colaboratori (sau verificare în log dev dacă mail nu e configurat). | L | [ ] |

**Ramuri suplimentare (înregistrezi în §3 dacă ceva nu merge)**

| Cod | Ce verifici | Status |
|-----|-------------|--------|
| AD-R1 | Proprietar **respinge** cererea — adoptator vede respins; **fără** finalize. | [ ] |
| AD-R2 | Proprietar **prelungește** termen (`extend`). | [ ] |
| AD-R3 | Listă așteptare: a doua cerere rămâne pending când prima e acceptată; **`next`** când e cazul. | [ ] |
| AD-R4 | Proprietar acceptă din **e-mail** (link `adoption/email/<token>/...`), nu doar din MyPet. | [ ] |
| AD-R5 | Transport: **nimeni în zonă** — job `exhausted`, utilizator primește mesaj/e-mail adecvat (testează cu județ fictiv sau transportator inactiv). | [ ] |

---

*Lot **AD** — program extins; bifările se fac la **OK** pe fiecare pas (mod de lucru ca la N3).*

---

## 3. Registru constatări — **ce e de corectat** (completăm împreună)

*Format: o linie = o problemă sau o îndoială. Nu reparăm acum, doar înregistrăm.*

| # | Data | Lot | Rol | Unde (pagină / buton) | Ce s-a întâmplat | Propunere remediere (scurt) |
|---|------|-----|-----|------------------------|------------------|----------------------------|
| 1 | 2026-04-10 | Lot1 nav | Vizitator | `/login/` (după MyPet pas 7) | Caseta de login **nu e centrată vertical** (prea jos sau spațiu neechilibrat sus/jos); **stânga–dreapta OK**. | **Remediat** (Apr 2026): `login.html` — `100svh`/`100dvh`, `box-sizing`, `#main_content` cu selector care bate padding-ul navbar + flex centrat. **Reverificare tabletă** la următoarea probă. |
| 2 | | | | | | |

*(Adaugă rânduri după cum mergeți.)*

---

## 4. Pasul curent — **ce urmează** (fără repetare probe)

**Programul din §2bis** pentru fazele V… ST-P1 și Lot **N3** este deja parcurs. **Continuarea principală QA manuală:** Lot **AD** (§2bis), plus **§3** pentru constatări.

**Continuarea reală:**

1. **Lot AD** — `python scripts/qa_adoption_transport_setup.py` (+ `seed_portfolio` dacă trebuie), apoi pașii **AD-P0…** și matricea **M1–M9** (laptop + tabletă + telefon).
2. **§3 Registru constatări** — probleme la Lot AD sau alte probe; adaugi rânduri (#2, #3…).
3. **N2** / **Partea N** — opțional (vezi §1D).

**Mod de lucru:** în chat, **un mesaj = un singur pas** (ex. AD-P2); răspuns **OK** / **NU**; agentul bifează în acest fișier.

---

*Fișier de lucru QA. Ultima actualizare: Lot **AD** (matrice M1–M9, pași AD-P*, script `qa_adoption_transport_setup.py`) + §4.*
