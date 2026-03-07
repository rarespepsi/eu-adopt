# Referință proiect – context pentru chat-uri noi

*Document creat ca să aibă asistentul la dispoziție decizii, ce e făcut și unde sunt lucrurile. Actualizat după conversații.*

**Cum se folosește:** La fiecare conversație nouă se încarcă automat regula **`.cursor/rules/idei-principale-proiect.mdc`** (lista scurtă de idei principale). Pentru detalii: „Citește REFERINTA_PROIECT.md”.

---

## 1. FĂCUT (implementat)

### Pagini și rute
- **Home:** un singur template – `home_v2.html`, body class `page-home-v2`. Nu există „home vechi” live.
- **Prietenul tău (PT):** `pets-all.html`, URL `pets_all`. Filtrele sunt în **P3** (sidebar stânga).
- **Găsește-mi prietenul ideal:** `/match/quiz/` (chestionar), `/match/results/` (rezultate). Buton în P3 pe PT.

### Funcționalități
- **Match quiz:** formular 1 coloană; user nelogat → răspunsuri în sesiune (`match_quiz_draft`), mesaj „Am găsit X potriviri, autentifică-te”; user logat → salvare în `UserMatchProfile`, redirect la rezultate. După login cu draft în sesiune → salvare automată în profil + redirect la rezultate.
- **Filtre PT:** tip, județ, talie, vârstă (slider dublu 0–20), sex. Persistate în sesiune până la logout. Filtru vârstă = `age_years` (interval min–max); implicit 0–20 = fără filtru vârstă.
- **Postare animal:** formular standard cu secțiuni (Identitate, Locație & status, Sănătate, Comportament & potrivire, Poveste, Media). Min 3 poze obligatorii; video opțional (URL). Câmpuri matching: energy_level, size_category, age_category, good_with_children/dogs/cats, housing_fit, experience_required, attention_need; sanitar: sterilized_status, vaccinated_status, dewormed_status, microchipped_status (Da/Nu/În curs/Necunoscut).

### Model / DB
- **Pet:** `age_years` (0–20, întreg, obligatoriu la postare). `varsta_aproximativa` există în continuare (alt câmp). Filtrarea pe PT folosește `age_years`.
- **UserMatchProfile** (accounts): OneToOne User, câmpuri pentru chestionar match (housing, experience, activity_level, time_available, has_kids, has_cat, has_dog, size_preference, age_preference).

### UI / CSS
- **A0 (navbar):** setări în `navbar-a0-secured.css`. Pe home: `body.page-home-v2`. Contor comun (font) pentru toate contoarele site.
- **PT:** fără `pets-all-debug.css` (eliminat – nu mai sunt borduri colorate/dashed pe containere).
- **Slot-uri:** doar conținutul din sloturi se modifică; pozițiile sloturilor (layout) nu se schimbă (regulă Cursor).

---

## 2. DE PUS ÎN PRACTICĂ (când e cazul)

- **Reset date la lansare** – ștergere date fictive (users, animale); management command sau admin.
- **Verificare** – după modificări pe home/PT: fără scroll orizontal, centrat, fără borduri debug.

*Pentru mai multe idei/taskuri amânate:* vezi `ARHIVA_IDEI_TASKURI_SI_PROPUNERI.md`.
- **Procedură Adopție + Servicii (carduri parteneri):** flux complet (finalizare adopție → redirect Servicii, alegere 1–3 servicii, mailuri adoptator + prestatori) – vezi `PROCEDURA_ADOPTIE_SI_SERVICII.md`.
- **Pagina Servicii – date colaboratori:** acum cardurile din zone 3/4/5 folosesc poze și texte aleatorii. Când vor exista colaboratori reali, se vor folosi **poza și datele din fișa partenerului** (profil/fiche colaborator), nu surse aleatorii.

---

## 3. DECIZII ȘI PREFERINȚE

- **Layout:** Nu schimbăm pozițiile coloanelor/sloturilor; doar conținutul din sloturi (regulă slot-content-only).
- **Home:** Setări finale în `HOME_SETTINGS_REFERENCE.md`; la „reparări” care strică layout-ul, revii la valorile din acel fișier.
- **Filtre:** Live (fără buton Aplică); vârstă = doar cifre (slider min–max), fără dropdown categorii pe filtru.
- **Conversații lungi:** Pentru task nou, chat nou; detaliile importante rămân în acest fișier și în regulile `.cursor/rules/`.

---

## 4. TEHNIC / UNDE SUNT LUCRURILE

| Ce | Unde |
|----|------|
| View home | `anunturi.views.home` → `home_v2.html` |
| View PT (lista animale) | `anunturi.views.pets_all` |
| Filtre PT, sesiune | `SESSION_KEY_PETS_ALL_FILTERS`, `filter_keys`: tip, sex, marime, judet, varsta_min, varsta_max |
| Formular postare animal | `PetAdaugaForm`, secțiuni `PET_ADAUGA_SECTIONS` în `forms.py` |
| Match quiz / rezultate | `match_quiz_view`, `match_results_view`; `compute_matches()` în `match_utils.py` |
| Sesiune draft match (nelogat) | `SESSION_KEY_MATCH_QUIZ_DRAFT` = `"match_quiz_draft"`; la login cu draft → salvare în UserMatchProfile, redirect la `/match/results/` |
| Reguli Cursor | `.cursor/rules/` (slot-content-only, home-settings-reference, undo la pauză) |
| Setări home | `HOME_SETTINGS_REFERENCE.md`, `static/css/home-sidebar-compact.css` |
| Arhivă idei / taskuri | `ARHIVA_IDEI_TASKURI_SI_PROPUNERI.md` |

---

---

## 5. Cum actualizezi acest fișier

După conversații importante (feature nou, decizie de proiect): adaugă 1–2 fraze la **Făcut** sau la **Decizii**. Astfel în chat-uri noi va fi clar ce s-a stabilit.

---

*Actualizat: februarie 2026 – rezumat conversații și decizii.*
