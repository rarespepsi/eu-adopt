# Proceduri și puncte de verificare la finalizarea site-ului

Document pentru verificare și control la lansare. Toate aceste puncte trebuie verificate și, unde e cazul, actele/textele finalizate.

---

## 1. Emailuri trimise către clienți

### 1.1 Reminder 72h – wishlist (câinii neadoptați)
- **Ce:** După 72 de ore de la „Te plac”, dacă animalul nu e adoptat, doritorul primește un email cu toți câinii bifați și un mesaj. **Doar dacă a bifat opt-in** (notificări wishlist). Max 1 email la 7 zile per user.
- **Unde:** Comandă `python manage.py send_wishlist_72h_reminders` (rulează zilnic prin cron).
- **Fișier:** `anunturi/management/commands/send_wishlist_72h_reminders.py`
- **Opt-in:** Checkbox la înregistrare (PF/SRL/ONG) + în Cont → Profil: „Accept notificări email EU-Adopt (wishlist)”. Câmp `Profile.email_opt_in_wishlist`.
- **Dezabonare:** Toate emailurile wishlist conțin link „Dezabonare” (view `wishlist_unsubscribe` cu token signed).
- **De verificat:** Textul mesajului din email (subject + body) – la final se construiește mesajul definitiv.

### 1.2 Email la adopție (utilizator cu „Te plac”)
- **Ce:** Când un animal din wishlist este adoptat, utilizatorul primește un email vesel: anunț adopție, mulțumim, invitație să viziteze site-ul + **3 animale recomandate** (același tip/mărime/vârstă). **Excepție:** acest email nu e blocat de limita 7 zile. Conține link dezabonare.
- **Unde:** Signal în `anunturi/signals.py` – `notify_wishlist_users_when_adopted`.
- **De verificat:** Formularea finală a emailului.

### 1.3 Email 30 zile – „Încă îți cauți prietenul perfect?”
- **Ce:** Utilizatori cu **opt-in** care au adăugat prima dată un animal la wishlist acum 30+ zile, care **nu au primit încă** acest follow-up și respectă limita 7 zile. Email cu **4–6 animale recomandate** + link dezabonare.
- **Unde:** Comandă `python manage.py send_informal_30day` (rulează zilnic prin cron).
- **Fișier:** `anunturi/management/commands/send_informal_30day.py`
- **De verificat:** Textul mesajului (subject + body).

### 1.4 Alte emailuri existente
- Cerere adopție → ONG (link validare).
- Validare ONG → adoptator (date contact).
- Follow-up post-adopție (3/6 luni) – comanda `send_post_adoption_followups`.

**La finalizare:** Verificare legală/redacțională a tuturor emailurilor și actelor trimise către clienți.

---

## 2. Termeni și condiții

### 2.1 Conținutul termenilor și condițiilor
- **Status:** DE FĂCUT – textul complet al termenilor și condițiilor trebuie scris și validat (avocat / juridic).
- **Pagină existentă:** `/termeni/` – template `anunturi/termeni.html`. Momentan conține un text sumar și notă că va fi completat.

### 2.2 La creare cont (implementat)
- La înregistrare (PF, SRL, ONG): **bifă obligatorie** „Accept termenii și condițiile”.
- **Link** „Termeni și condiții” deschis într-un tab nou, ca persoana să poată citi înainte de a bifa.
- Formulare: câmp `accept_termeni` (required) în `RegisterPFForm`, `RegisterSRLForm`, `RegisterONGForm`.
- Template-uri: `register_pf.html`, `register_srl.html`, `register_ong.html` – afișează checkbox + link.

**De făcut la finalizare:** Scrierea și validarea conținutului real al paginii Termeni și condiții.

---

## 3. Alte proceduri de verificat

### 3.1 Flux adopție
- Nelogat apasă „Vreau să-l adopt” / „Aplică pentru adopție” → redirect la login cu `next` la pagina câinelui → după login revine la animal.
- Formular adopție vizibil doar pentru utilizatori autentificați.

### 3.2 Wishlist (Te plac)
- Buton „Te plac” lângă poza fiecărui animal (listă + pagină animal).
- Casetă „Te plac” + număr în A0 (și header pets-all / pets-single) – link către pagina listă.
- Pagină listă: `/wishlist/` (alias `/my-wishlist/`) – **toate** animalele salvate, cu **badge status** (Disponibil / Adoptat / Rezervat) + buton „Scoate din listă” per animal.
- **Opt-in notificări:** la înregistrare (PF/SRL/ONG) + în Cont → Profil. Dezabonare: link în fiecare email wishlist → `/wishlist/unsubscribe/<signed>/`.

### 3.3 Setări tehnice
- **SITE_URL** (settings / env) – pentru linkuri în emailuri.
- **DEFAULT_FROM_EMAIL**, **EMAIL_HOST** etc. – pentru trimitere email real în producție.
- Cron (ex. zilnic): `send_wishlist_72h_reminders`, `send_informal_30day`, eventual `send_post_adoption_followups`.

---

## 4. Rezumat pași la finalizare

1. **Termeni și condiții:** Scrie și validează conținutul; actualizează `termeni.html`.
2. **Emailuri:** Verifică și aprobă textele din: reminder 72h, email adopție (signal), email 30 zile, celelalte (cerere adopție, validare, follow-up).
3. **Acte și conformitate:** Verificare finală a tuturor mesajelor și actelor trimise către clienți.

---

*Document creat pentru verificare și control la finalizarea site-ului EU Adopt.*
