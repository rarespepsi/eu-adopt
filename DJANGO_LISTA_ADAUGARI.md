# Listă – ce s-a pus în Django (proiect euadopt)

**Deschizi proiectul mâine? Citește acest fișier prima dată – conține tot ce a fost adăugat în Django.**

---

## 1. Modele (home/models.py)

| Model | Rol |
|-------|-----|
| **UserProfile** | Profil extensie pentru User (persoană fizică). Câmpuri: `user` (OneToOne), `phone`, `oras`, `poza_1` (ImageField), `accept_termeni`, `accept_gdpr`, `email_opt_in_wishlist`, `created_at`, `updated_at`. |
| **UserAdoption** | Adopții făcute de user. Câmpuri: `user` (FK), `animal_id`, `animal_name`, `animal_type`, `source`, `status` (pending/approved/completed/cancelled), `requested_at`, `updated_at`. |
| **UserPost** | Postări user (anunțuri, povești, donații). Câmpuri: `user` (FK), `post_type` (adoption_request, adoption_story, donation, service, other), `title`, `body`, `is_published`, `created_at`, `updated_at`. |

*(User vine din django.contrib.auth – date_joined, last_login, username, email, first_name, last_name, password.)*

---

## 2. Migrări (home/migrations/)

- **0001_signup_pf_profile.py** – creează tabelul `UserProfile`.
- **0002_user_extra_models.py** – creează tabelele `UserAdoption` și `UserPost`.

*(Rulezi: `python manage.py migrate` dacă ai clonat proiectul pe alt PC.)*

---

## 3. Admin (home/admin.py)

- **UserProfile** – list_display: user, phone, oras, created_at. Search pe email, nume, telefon, oraș.
- **UserAdoption** – list_display: user, animal_name, animal_type, status, requested_at. Filtre: status, animal_type, source.
- **UserPost** – list_display: user, post_type, title, is_published, created_at. Filtre: post_type, is_published.

---

## 4. URL-uri noi (home/urls.py)

| URL | Name | View |
|-----|------|------|
| `/login/` | login | login_view |
| `/login/forgot-password/` | forgot_password | forgot_password_view |
| `/signup/alege-tip/` | signup_choose_type | signup_choose_type_view |
| `/signup/persoana-fizica/` | signup_pf | signup_pf_view |
| `/signup/organizatie/` | signup_organizatie | signup_organizatie_view |
| `/signup/colaborator/` | signup_colaborator | signup_colaborator_view |

*(Plus cele existente: home, servicii, transport, custi, shop, shop_comanda_personalizate, shop_magazin_foto, pets_all, pets_single.)*

---

## 5. View-uri noi (home/views.py)

- **login_view** – randerează login.html.
- **forgot_password_view** – randerează forgot_password.html.
- **signup_choose_type_view** – randerează signup_choose_type.html.
- **signup_pf_view** – randerează signup_pf.html (formular PF; nu salvează încă în DB).
- **signup_organizatie_view** – randerează signup_organizatie.html.
- **signup_colaborator_view** – randerează signup_colaborator.html.

---

## 6. Template-uri noi (templates/anunturi/)

- **login.html** – pagină autentificare (email, parolă, link forgot password, signup).
- **forgot_password.html** – pagină „Ți-ai uitat parola?”.
- **signup_choose_type.html** – alegere tip cont (PF / Organizație / Colaborator) + reguli site.
- **signup_pf.html** – formular înregistrare persoană fizică (nume, prenume, email, telefon, oraș, parolă, accept termeni/GDPR, wishlist, poză profil; casete semitransparente, fundal Transport).
- **signup_organizatie.html** – formular înregistrare organizație (placeholder).
- **signup_colaborator.html** – formular înregistrare colaborator (placeholder).

---

## 7. Setări proiect (euadopt_final/settings.py)

- **MEDIA_URL** = `'media/'`
- **MEDIA_ROOT** = `BASE_DIR / 'media'`  
  (pentru upload poză profil și alte fișiere utilizator.)

---

## 8. URL-uri media (euadopt_final/urls.py)

- În DEBUG: servire fișiere din `MEDIA_ROOT` la `MEDIA_URL` (ca pozele încărcate să se vadă în dev).

---

## Ce nu e făcut încă (de verificat / implementat)

- **Salvare la „Creează cont”** – view-ul signup_pf nu scrie în DB; trebuie legat formularul la User + UserProfile (generare username, set_password, salvare profil).
- **Formulare Organizație / Colaborator** – doar UI; modele/view-uri specifice (dacă vrei) n-au fost adăugate.
- **Legare adopții** – UserAdoption există; butoanele „Adoptă” din site nu creează încă înregistrări.
- **Legare postări** – UserPost există; pagini de creare anunț/postare nu sunt legate încă.

---

*Fișier generat pentru sesiunea curentă. La deschiderea proiectului, cere: „dă-mi lista cu ce ai pus în Django” – poți folosi acest fișier.*
