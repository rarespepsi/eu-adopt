# ⚠️ FIȘIER VECHI – CONȚINUT CENTRALIZAT

**📚 Acest fișier a fost centralizat în `DOCUMENTATIE_CENTRALIZATA.md`**  
**Nu mai actualiza acest fișier – folosește fișierul centralizat pentru a evita duplicarea informațiilor.**

---

# Formulare adopție – notițe și categorisire

Document unic: ce formulare avem, ce mai avem nevoie, ce nu trebuie uitat.

---

## 1. Formulare existente (deja în platformă)

| Formular | Unde | Scop |
|----------|------|------|
| **Formular cerere adopție** | Pagina animalului (`/pets/<id>/adoption/`) | Vizitatorul completează: nume complet, email, telefon, adresă, mesaj, ridicare personală Da/Nu, opțiuni transport/cazare medicală. |
| **Validare platformă** | Automată (backend) | Verificare condiții: nume 2+ cuvinte, telefon 10+ cifre, mesaj/adresă în limite. Dacă trece → trimitere email la ONG cu link validare. |
| **Validare ONG** | Link în email (unic) | ONG apasă pe link → se trimit datele adoptatorului către ONG și cartea de vizită către adoptator; cererea devine „Validată de ONG”. |

---

## 2. Formular verificare post-adopție + angajament adoptator

**De nu uitat:** formularul de **verificare post-adopție** nu este folosit în mod obișnuit în țara noastră, dar îl setăm pentru bunăstarea animalului.

- **Angajament adoptator:** prin validarea cererii de adopție, adoptatorul **își asumă** că la fiecare **6 luni** va trimite **o poză sau mai multe** cu animalul (câinele), ca platforma/asociația să verifice dacă totul este în regulă.
- **Formular verificare post-adopție:** implementat – pagină `/adoption/verificare/<token>/` (link în emailul de follow-up), mesaj + opțional 3 poze (max 2 MB). Răspunsurile în admin la „Răspunsuri verificare post-adopție”.

---

## 3. Email automat la 3 sau 6 luni după adopție finalizată

- La fiecare **adopție finalizată** (status `approved_ong`) se trimite **automat** un email la **3** sau **6 luni** în care **ne interesăm de soarta animalului** (link către formularul de verificare post-adopție).

**Implementare:** Comandă `python manage.py send_post_adoption_followups` (opțional `--months 6`, `--dry-run`). Setare `POST_ADOPTION_FOLLOWUP_MONTHS = 6` în settings. Programare cron pe server (ex. zilnic).

---

## 4. Rezumat acțiuni

- [x] Notițe formulate (acest document în folderul principal).
- [x] Formular verificare post-adopție (pagină + model + admin).
- [x] Comandă send_post_adoption_followups + email 3/6 luni.
- [ ] Programare cron pe server.
- [x] Mențiune angajament (poze la 6 luni) în emailul către adoptator după validare.

---

## 5. Convenții formulare

**De acum înainte:** unde trebuie create formulare și nu avem încă toate datele/câmpurile finale, creăm formularul cu ce date avem și pe parcurs **doar modificăm** (adăugăm sau ajustăm câmpuri). Nu așteptăm lista completă; iterăm.

**Faza curentă:** construim **baza** (fluxuri, categorii, date esențiale). Finisaje, rafinări și „finete” le facem când lucrăm explicit la ele.

---

## 6. Verificare online CUI/CIF (membri cu date oficiale)

Script și surse pentru verificarea veridicității informațiilor (CUI/CIF) ale membrilor:

| Tip        | Surse (gratuit) |
|-----------|------------------|
| **SRL**   | termene.ro (date de bază), listafirme.ro (date principale) |
| **ONG/AF**| portal.just.ro → Registrul Național ONG (registrul oficial)   |

- **Modul:** `anunturi/official_verification.py` – `verify_srl_cui()`, `verify_ong_registry()`, `verify_member_official_data()`.
- **Comandă:** `python manage.py verify_cui_members` (opțional `--user ID`, `--verbose`).
- **Setări:** `LISTAFIRME_API_KEY` (dacă e setat, se folosește API listafirme.ro); pe parcurs se pot adăuga alte API-uri.

---

## 7. De nu uitat – checklist și repere

**Cron / automatizări**
- [ ] Cron (ex. zilnic) pentru `python manage.py send_post_adoption_followups` – email follow-up la 3/6 luni după adopție finalizată.

**Limite și reguli de business**
- Persoane fizice: **max 2 anunțuri (animale) pe lună** – `POSTS_PER_MONTH_PF = 2` în settings; verificare în `cont_persoana_adauga_animal`.
- Adoptator: angajament **6 luni** – poze/verificare; email automat la 3 sau 6 luni cu link formular verificare post-adopție.

**Înregistrare / tip cont (3 categorii)**
- 1 = Persoană fizică (UserProfile).
- 2 = SRL / PFA / Asociație sau Fundație → sub-alegere SRL, PFA sau AF (OngProfile, grup „Asociație”).
- 3 = ONG / Asociație de profil (OngProfile, grup „Asociație”).
- Un singur document/formular de categorii – nu duplicăm.

**Logare și URL-uri**
- Logare: `/cont/login/` (Django auth). Înregistrare: `/cont/inregistrare/`.
- Cont PF: `/cont/profil/` (profil + verificare telefon SMS, 6 casete cod). Cont ONG/SRL/PFA/AF: `/cont/ong/`.
- Adăugare animal PF: `/cont/adauga-animal/` (limitat 2/lună). Adăugare animal ONG: `/cont/ong/adauga/`.

**Verificare telefon (persoană fizică)**
- La Cont → Profil: câmp Telefon + mesaj că se primește cod SMS; secțiune „Verificare telefon” cu **6 casete** pentru cod; buton Validare (trimite cod / verifică cod). După validare: „Telefon verificat”.

**Verificare CUI/CIF**
- SRL/PFA: termene.ro, listafirme.ro. ONG/AF: portal.just.ro (Registrul Național ONG). Comandă `verify_cui_members`; opțional `LISTAFIRME_API_KEY`.

**Formulare – convenții**
- Formulare: creăm cu ce date avem, modificăm pe parcurs; nu așteptăm lista completă.
- Faza curentă: baza; finisajele (finete) când lucrăm explicit la ele.

**Tehnic**
- Migrări: după modificări modele, `manage.py makemigrations` + `migrate`.
- Grup utilizatori: „Asociație” pentru ONG/SRL/PFA/AF (acces Cont ONG, adăugare animale fără limită lună). PF: fără acest grup, limită 2 postări/lună.
- Pet: `ong_email` = contact adopție; `added_by_user` setat doar pentru animale adăugate de persoane fizice (pentru limită lună).
