# Utilizatori de test — cine e „tu” și cine e din scripturi

**Parole:** nu sunt aici; le ai tu.

**Conturi „reale” (confirmare titular):** au **adresă de e-mail reală** în site — userii: **`rares`**, **`rarespepsi`**, **`radu`**, **`nccristescu`**. Restul din scripturi (`dpf`, `dg1`, `e2e_*` …) sunt **demo** pentru probă (email de tip test / local, după cum i-ai creat).

---

## 0. Plansă completă pentru probe — **real (email real)** + **demo (script)**

**Ideea:** tipurile de cont vin din înregistrarea pe site; **patru conturi reale** acoperă parte din plansă; **demo-ii** completează rolurile lipsă.

| Tip cont (ca la înregistrare / rol în proiect) | **Cont real (e-mail real)** | **Cont demo (scripturi)** — completare pentru probă |
|-----------------------------------------------|----------------------------|------------------------------------------------------|
| **Persoană fizică (PF)** | — *(niciunul din cei 4 de mai sus nu e PF în listă)* | `dpf`, `e2e_pf`, `e2e_staff` |
| **ONG / adăpost public** | **`rarespepsi`** | — |
| **ONG / adăpost privat** | **`radu`** | — |
| **Colaborator cabinet (veterinar)** | **`nccristescu`** | — |
| **Colaborator servicii** | — | **`dg1`**, **`dg2`** |
| **Colaborator magazin** | — | **`dm`** |
| **Colaborator transport** | **`rares`** | — |
| **Staff / admin (navbar Analiză, Reclama)** | **`rares`** — *același cont are și drepturi de admin* (confirmat titular); altfel superuser creat manual | **`e2e_staff`** (*atenție:* `_align_user_roles` îi poate scoate staff-ul) |

**Cum sunt făcuți demo-ii:** nu înlocuiesc mereu un „Creează cont” click cu click — `e2e/create_e2e_users.py` creează useri în DB; `_align_user_roles.py` setează `AccountProfile` / `UserProfile`; `seed_portfolio.py` poate adăuga anunțuri/oferte `[seed]`. Scopul e **aceeași plansă de roluri** ca în proiect, pentru teste automate și QA manual.

**Împreună** (real + demo) acoperiți **toată plansa** de tipuri de user folosite la probe, aliniată cu `scripts/_align_user_roles.py`.

---

## A. Conturi cu **e-mail real** (titular)

| Username | Rol (aliniat `scripts/_align_user_roles.py`) |
|----------|---------------------------------------------|
| **rares** | Colaborator transport **și** cont **admin/staff** (navbar: **Analiză**, **Reclama**, **PUB** — verificat QA) |
| **rarespepsi** | ONG adăpost public |
| **radu** | ONG privat |
| **nccristescu** | Colaborator **cabinet veterinar** — în navbar eticheta panoului e **MyListVet** (`home/context_processors.py`); pagina oferte / control oferte. |

*(Username corect: **`nccristescu`** — confirmat titular; greșeală de scris anterioară „iccristescu”.)*

---

## B. Conturi **demo** (repo — scripturi), fără cerință „email real”

În `scripts/_align_user_roles.py`, `scripts/seed_portfolio.py`, `e2e/create_e2e_users.py`:

| Username | Rol în script |
|----------|----------------|
| **dg1** | colaborator servicii — navbar **MyListServicii** (în UI poate apărea „My list Servicii”) |
| **dg2** | colaborator servicii — același tip ca `dg1` |
| **dm** | colaborator magazin |
| **dpf** | PF |
| **e2e_pf** | PF (Playwright) |
| **e2e_staff** | staff la creare E2E; `_align_user_roles` îl poate face PF fără staff |

**`nccristescu`**, **`rares`**, **`rarespepsi`**, **`radu`** apar și în scripturi pentru aliniere/seed, dar la voi sunt **conturi reale** (secțiunea **A**), nu demo.

---

## C. Ce probăm pe scurt (după rol)

| Rol | Useri (unde găsești) |
|-----|----------------------|
| PF | `dpf`, `e2e_pf`, eventual `e2e_staff` după aliniere |
| ONG | `rarespepsi`, `radu` |
| Colaborator | **real:** `nccristescu`, `rares` — **demo:** `dg1`, `dg2`, `dm` |
| Staff | `e2e_staff` (dacă nu l-ai „tăiat” cu `_align_user_roles`) sau superuser din Admin |

---

## D. Adopție / mesaje — conturi cu **animale postate**

Pentru fluxuri de **adopție**, **cereri**, **mesaje de pe fișă**, ai nevoie de utilizatori care au **anunțuri publicate** (animale în MyPet / pe PT).

| Notă QA (2026-04) | Detaliu |
|-------------------|---------|
| Cont **PF** folosit la probă (ex. `dpf` sau `e2e_pf`) | În MyPet sunt **5 animale** vizibile — pot fi din date demo / `scripts/seed_portfolio.py` (anunțuri cu prefix **`[seed]`** în titlu dacă ai rulat seed-ul). |
| Pentru teste viitoare | **Păstrează** acest cont (sau orice PF cu animale live) ca **proprietar** când testezi: cerere adopție, accept/respinge, mesaje. |

Sursă tehnică: `scripts/seed_portfolio.py` poate popula **15 anunțuri / user PF** listat acolo (`dpf`, `e2e_pf`, `e2e_staff`); numărul exact pe ecran poate varia după ce rulezi scriptul sau editezi datele.

---

## E. Tabel unic — **aceeași sursă ca scriptul** (`_align_user_roles.py`)

*Agentul **compară** mereu cu acest tabel înainte să schimbe rolul unui username în doc; nu înlocuiește scriptul cu o interpretare dintr-un singur mesaj ambiguu.*

| Username | Rol în `scripts/_align_user_roles.py` |
|----------|----------------------------------------|
| `dpf`, `e2e_pf`, `e2e_staff` | PF (`set_pf`; `e2e_staff` poate pierde staff la același script) |
| **`rarespepsi`** | **ONG adăpost public** |
| **`radu`** | ONG privat |
| `nccristescu` | Colaborator cabinet (veterinar) |
| `dg1`, `dg2` | Colaborator servicii |
| `dm` | Colaborator magazin |
| **`rares`** | **Colaborator transport** |

**Conturi cu e-mail real (secțiunea A):** `rares`, `rarespepsi`, `radu`, `nccristescu` — trebuie să **coincidă** cu rândurile de mai sus din acest tabel.

---

## F. Fișiere unde sunt listate numele

- `scripts/_align_user_roles.py` — **sursa de adevăr rol × user** (înainte de orice notă QA)
- `scripts/seed_portfolio.py`
- `e2e/create_e2e_users.py`

---

*Actualizat: conturi reale = e-mail real — `rares`, `rarespepsi`, `radu`, `nccristescu`; demo = `dpf`, `dg*`, `dm`, `e2e_*`.*
