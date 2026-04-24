# QA — Verificare funcționalitate: logare → adopție (EU-Adopt)

**Document generat din rutele proiectului** (`home/urls.py`). Înlocuiește `BASE` cu URL-ul mediului (ex. `http://127.0.0.1:8000`).

**Data:** _______________ **Tester:** _______________ **Mediu:** _______________ **Commit / build:** _______________

---

## Legendă URL (relative la `BASE`)

| Zonă | URL | Nume rută Django (referință) |
|------|-----|--------------------------------|
| Acasă | `/` | `home` |
| Prietenul tău (listă PT) | `/pets/` | `pets_all` — șablon `anunturi/pt.html` |
| Fișă animal | `/pets/<pk>/` | `pets_single` — șablon `anunturi/pets-single.html` (din PT sau `BASE/pets/?go=<pk>` → redirect la fișă) |
| Cerere adopție (POST) | `/pets/<pk>/adopt/request/` | `pet_adoption_request` |
| Acțiune adopție din email | `/adoption/email/<token>/<decision>/` | `adoption_email_owner_action` |
| Bonus adopție (toggle / unlock) | `/adoption/bonus/toggle/`, `/adoption/bonus/cart-unlock/` | `adoption_bonus_offer_toggle`, `adoption_bonus_cart_unlock` |
| Logare | `/login/` | `login` — șablon `anunturi/login.html` |
| Logout | `/logout/` | `logout` |
| Parolă uitată | `/login/forgot-password/` | `forgot_password` |
| Reset parolă | `/login/reset-password/` | `reset_password` |
| Cont | `/cont/` | `account` |
| Mesaje unificate cont | `/cont/mesaje/` | `unified_inbox` |
| MyPet listă | `/mypet/` | `mypet` — șablon `anunturi/mypet.html` |
| Adaugă pet | `/mypet/add/` | `mypet_add` |
| Editare fișă pet | `/mypet/edit/<pk>/` | `mypet_edit` |
| Promovare A2 | `/mypet/promovare/<pk>/` | `promo_a2_order` |
| Accept adopție (POST) | `/mypet/adoption/<req_id>/accept/` | `mypet_adoption_accept` |
| Respinge (POST) | `/mypet/adoption/<req_id>/reject/` | `mypet_adoption_reject` |
| Prelungește (POST) | `/mypet/adoption/<req_id>/extend/` | `mypet_adoption_extend` |
| Următorul din listă (POST) | `/mypet/adoption/<req_id>/next/` | `mypet_adoption_next` |
| Finalizare adopție (POST) | `/mypet/adoption/<req_id>/finalize/` | `mypet_adoption_finalize` |
| Mesaje per pet (proprietar) | `/mypet/messages/<pk>/` | `mypet_messages_list` |
| Thread mesaje | `/mypet/messages/<pk>/<sender_id>/` | `mypet_messages_thread` |
| Răspuns (POST) | `/mypet/messages/<pk>/<sender_id>/reply/` | `mypet_messages_reply` |
| Inbox adoptator (fără pets proprii) | `/mypet/messages/adopter/` | `adopter_messages_list` |
| Thread adoptator | `/mypet/messages/adopter/<pk>/` | `adopter_messages_thread` |
| Răspuns adoptator (POST) | `/mypet/messages/adopter/<pk>/reply/` | `adopter_messages_reply` |
| Înregistrare PF | `/signup/persoana-fizica/` | `signup_pf` |
| Alege tip cont | `/signup/alege-tip/` | `signup_choose_type` |
| ONG | `/signup/organizatie/` | `signup_organizatie` |
| Colaborator | `/signup/colaborator/` | `signup_colaborator` |
| Verificare SMS (signup) | `/signup/verificare-sms/` | `signup_verificare_sms` |

---

## 1. Pregătire date

- [ ] Cont **proprietar** (animal publicat): _______________
- [ ] Cont **adoptator** (PF, `can_adopt_animals` ok): _______________
- [ ] Cont **ONG** (dacă testezi flux ONG): _______________
- [ ] Cont **colaborator** (dacă e relevant pentru restricții): _______________
- [ ] `pk` animal publicat pentru teste: _______________
- [ ] `req_id` cerere adopție (după ce există): _______________
- [ ] Inbox email pentru link-uri `/adoption/email/.../`

---

## 2. Înregistrare & activare (dacă testezi conturi noi)

- [ ] `/signup/alege-tip/` — alegere tip
- [ ] `/signup/persoana-fizica/` (sau ONG / colaborator) — formular trimis
- [ ] `/signup/verificare-sms/` — cod SMS (dacă e activ în mediu)
- [ ] `/signup/verificare-email/` / activare (după caz)
- [ ] `/signup/complete-login/` — continuare după signup

---

## 3. Logare & sesiune

- [ ] `BASE/login/` — afișare corectă, fără erori
- [ ] Logare reușită → redirect așteptat (ex. home sau `next`)
- [ ] `BASE/login/?demo=1` — doar dacă folosiți prefill demo (comportament documentat)
- [ ] Parolă greșită → mesaj, fără crash
- [ ] `BASE/login/forgot-password/` → flux până la mesaj
- [ ] `BASE/login/reset-password/` — cu token valid
- [ ] `BASE/logout/` — sesiune terminată; `/mypet/` sau `/cont/` cer logare

---

## 4. Prietenul tău (PT) & fișă animal

- [ ] `BASE/pets/` — listă P2, filtre, scroll / `pets/p2-more/` (JSON) dacă testați infinit scroll
- [ ] Deschidere `BASE/pets/<pk>/` — `pets-single.html`, date animal
- [ ] Utilizator neautentificat: butoane vizibile conform regulilor (adopție / mesaj)
- [ ] `can_send_pet_message` / mesaj către proprietar (dacă e cazul): `POST BASE/pets/<pk>/message/`
- [ ] Wishlist: `POST site-cart/toggle/` sau `wishlist/toggle/` (după implementare navbar)

---

## 5. Cerere adopție (adoptator → animal)

- [ ] Pe `pets-single`, acțiune **„Vreau să adopt”** / cerere (UI)
- [ ] `POST BASE/pets/<pk>/adopt/request/` — răspuns JSON succes
- [ ] Caz: adoptator **fără** drept adopție (`can_adopt_animals` false) — mesaj / blocare
- [ ] Caz: proprietarul încearcă să adopte propriul animal — respins
- [ ] Caz: animal deja **adoptat** / indisponibil — mesaj clar
- [ ] După cerere: stare afișată pe fișă (`adoption_request_status` în context)

---

## 6. Proprietar — MyPet & acțiuni adopție

- [ ] `BASE/mypet/` — tabel, filtre specii, coloane adopție
- [ ] Cerere **pending**: afișare ✓ / ✕ (accept / respinge) dacă e în UI
- [ ] `POST BASE/mypet/adoption/<req_id>/accept/` — după confirmare UI; email; reload
- [ ] `POST BASE/mypet/adoption/<req_id>/reject/` — idem
- [ ] Buton **⚙** manage: prelungire `.../extend/` (dacă `data-can-extend`)
- [ ] Buton **⚙** / flux: **următorul** `.../next/` (dacă `data-can-next`)
- [ ] Buton **FIN** finalize: `POST .../finalize/` — animal marcat adoptat; contor „Adoptați”
- [ ] Eroare rețea / răspuns `ok: false` — alertă; butoane reactivate

---

## 7. Link din email (proprietar fără să intre în MyPet)

- [ ] Deschidere `BASE/adoption/email/<token>/accept/` (sau `reject` / variantă din email) — `adoption_email_owner_action`
- [ ] Token invalid / expirat — mesaj controlat
- [ ] După acțiune, stare animal / cerere coerentă în UI

---

## 8. Mesaje (adopție în curs / acceptată)

**Proprietar (din listă pet):**

- [ ] `BASE/mypet/messages/<pk>/` — listă thread-uri
- [ ] `BASE/mypet/messages/<pk>/<sender_id>/` — citire thread
- [ ] `POST .../reply/` — răspuns

**Adoptator (fără animale proprii pe MyPet):**

- [ ] `BASE/mypet/messages/adopter/` — inbox
- [ ] `BASE/mypet/messages/adopter/<pk>/` — thread
- [ ] `POST .../reply/` — răspuns

**Cont general:**

- [ ] `BASE/cont/mesaje/` — `unified_inbox` (dacă include conversații adopție)

---

## 9. Bonus adopție (dacă folosiți în produs)

- [ ] `POST BASE/adoption/bonus/toggle/`
- [ ] `POST BASE/adoption/bonus/cart-unlock/`

---

## 10. Edge & securitate

- [ ] Două cereri de la adoptori diferiți pe același animal — ordine / listă așteptare
- [ ] Double-click rapid pe Accept — un singur efect (busy / disabled)
- [ ] CSRF invalid la POST adopție — eroare clară
- [ ] Mobile: butoane MyPet accesibile, scroll tabel

---

## 11. Închidere

- [ ] `BASE/logout/`
- [ ] Defecte notate: _________________________________________________

---

## 12. Backlog — de făcut la final (notat din discuție)

*Lista de lucru / clarificări; le bifați pe rând când le abordați.*

### A. Flux adopție (după Servicii / Shop)

- [ ] MyPet proprietar: accept / respinge / prelungire / următorul / finalizare
- [ ] Mesaje adoptator ↔ proprietar (inbox MyPet / `unified_inbox`)
- [ ] Link email proprietar (`/adoption/email/.../`) — accept fără login
- [ ] Mailuri bonus adopție (primire, Spam, subiect `[username]`)
- [ ] Transport în tur: formular, dispatch; eventual **cereri vechi `TransportVeterinaryRequest`** cu alt județ (nu migrate la Iași în QA)

### B. Mediu & date QA

- [ ] `EUADOPT_RELAX_EMAIL_UNIQUE` — dezactivat când nu mai testați cu același inbox
- [ ] Conturi `dg2` etc. — parole verificate / reset
- [ ] Oferte colaboratori în afara `[QA-Iasi]` — verificare vizuală filtre / locație

### C. Shop & bonus (produs / UX)

- [ ] `shop_view` placeholder — conținut real, legătură coș / coduri după bonus
- [ ] Redirect după accept bonus: **Shop** vs **MyPet** vs **fișă animal** / **Servicii** — decizie produs
- [ ] Coș site (`site_cart`) — flux complet sau demo

### D. Calitate

- [ ] Acest document (secțiunile 1–11) — parcurs cap-coadă pe dispozitive
- [ ] Performanță / CSRF / dublu-click (inimioară, „Salvează alegerile”)
- [ ] Modificări pe pagini înghețate (HOME, PT, Shop, Navbar…) — doar cu parola proiectului, explicit

### E. Opțional tehnic

- [ ] Script / comandă pentru `TransportVeterinaryRequest.judet/oras` → Iași (dacă vreți istoric aliniat)
- [ ] Backup DB înainte de scripturi în masă pe alt mediu

### F. UI Servicii (rezolvat, rămâne verificat la final)

- [x] Badge discount pe carduri: **centrat sus** (nu suprapunere cu inimioară) — `templates/anunturi/servicii.html`

---

*Ultima actualizare rută: `home/urls.py` (include sub `path('', include('home.urls'))`).*
