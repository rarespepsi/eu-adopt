# Raport: Spec ChatGPT (Wishlist + Email) vs implementare curentă

Comparație între comanda ChatGPT „EU-Adopt Wishlist + Email Automation” și ce există deja în proiect.  
**✅ = făcut** | **⚠️ = parțial / diferit** | **❌ = nefăcut**

---

## 1) Wishlist core

| Cerință | Status | Detalii |
|--------|--------|---------|
| Buton „Te plac ❤️” pe pagina animal | ✅ | Pe pets-single (zona poză) + pe cards pets-all |
| Nelogat → login → return la aceeași pagină animal | ✅ | `wishlist_toggle` redirect login cu `next=...?add_to_wishlist=1`, `pets_single` adaugă la wishlist la GET |
| Persistență în DB (nu localStorage) | ✅ | Model `PetFavorite`: user, pet, created_at, notified_adopted, reminder_72h_sent_at |
| Pet.status: available \| reserved \| adopted \| unavailable | ⚠️ | Avem: adoptable, pending, adopted, showcase_archive (echivalent funcțional) |
| WishlistItem: removed_at, last_notified_at | ⚠️ | Avem `PetFavorite` fără `removed_at` (ștergem la remove). Avem `reminder_72h_sent_at` (echivalent last_notified_at pentru 72h). |

---

## 2) A0 counter + pagină listă

| Cerință | Status | Detalii |
|--------|--------|---------|
| Badge wishlist în A0 (❤️ 0..N) | ✅ | Casetă „Te plac” + număr în base.html (A0), pets-all, pets-single |
| Pagină listă wishlist | ✅ | `/wishlist/` (name: `wishlist`). Spec cere `/my-wishlist/` – poți adăuga alias dacă vrei |
| Listă cu status + buton remove | ⚠️ | Avem remove per animal. **Nu** afișăm statusul animalului (adoptable/adopted). Spec: „Saved pets remain until user removes or pet becomes unavailable/adopted (**keep visible but show status**)” – la noi animalele adoptate sunt filtrate (notified_adopted) și nu apar în listă. |

**Modificare opțională:** Pe pagina wishlist să afișezi toate favoritele (inclusiv cele cu pet adoptat) și lângă fiecare să apară un badge de status (Disponibil / Adoptat etc.).

---

## 3) Email opt-in + anti-spam

| Cerință | Status | Detalii |
|--------|--------|---------|
| Checkbox „Accept notificări email EU-Adopt (wishlist)” la signup | ❌ | Nu există. Trimitem fără opt-in. |
| Checkbox în account/settings | ❌ | Nu există. |
| Câmp user / profile: email_opt_in_wishlist (boolean) | ❌ | Nu există. |
| Max 1 wishlist email per user la 7 zile | ❌ | Nu există limită. |
| Excepție: email „adoptat” poate fi trimis imediat | N/A | Dacă se adaugă limita de 7 zile, trebuie excepție pentru acest email. |
| Toate emailurile wishlist cu link unsubscribe (setează email_opt_in_wishlist = false) | ❌ | Nu există. |

**De făcut:**  
- Adăugare câmp `email_opt_in_wishlist` (ex. pe `Profile`, sau pe User dacă preferi).  
- Checkbox la înregistrare (PF/SRL/ONG) + în setări cont (profil).  
- În comanda 72h și în emailul 30 zile: trimite doar dacă `email_opt_in_wishlist=True` și (opțional) respectă limita de 7 zile (`last_wishlist_email_at`).  
- View + URL pentru unsubscribe (token sau link pentru user logat) care seteaază `email_opt_in_wishlist=False`.  
- În fiecare email wishlist: link „Dezabonare” către acel URL.

---

## 4) Emailuri automate (scheduler)

| Cerință | Status | Detalii |
|--------|--------|---------|
| **A) 72h reminder** | | |
| Pentru user cu opt-in, cu item activ (removed_at IS NULL), creat acum 72h+, never reminded | ✅ | Filtru: pet adoptable, created_at ≤ 72h, reminder_72h_sent_at NULL. **Fără** verificare opt-in și fără limită 7 zile. |
| Email cu 1–3 wishlist pets (poză, nume, link), CTA la /my-wishlist/ | ⚠️ | Trimitem listă de animale + linkuri. Fără poze în email (doar text). Fără verificare opt-in. |
| Set last_notified_at și last_wishlist_email_at | ⚠️ | Setăm `reminder_72h_sent_at` pe item. **Nu** avem `last_wishlist_email_at` pe user. |
| **B) Status → adopted** | | |
| La trecere Pet la adopted, email imediat „Prietenul tău și-a găsit familie” | ✅ | Signal `notify_wishlist_users_when_adopted` în `signals.py`. |
| 3 animale recomandate (specii + mărime + vârstă), excl. adopted/unavailable | ❌ | Nu sunt în email. |
| **C) 30-day follow-up** | | |
| Pentru user cu opt-in, first wishlist add ≥ 30 zile, nu emailuit în ultimele 7 zile | ⚠️ | Avem `send_informal_30day` dar altă logică: orice membru cu profil, la 30 zile (last_informal_email_sent_at). **Nu** e „Încă îți cauți prietenul perfect?” cu 4–6 animale recomandate. |
| Mesaj „Încă îți cauți prietenul perfect?” + 4–6 recommended pets | ❌ | Mesajul nostru e „Mulțumim, apreciem”. Fără recommended pets. |
| last_followup_30d_at ca să nu se repete | ⚠️ | Avem `Profile.last_informal_email_sent_at` (un singur tip de email la 30 zile). |

**Scheduler:** Spec cere Celery + Beat (sau Django-Q/cron). La noi: **cron + management commands** (`send_wishlist_72h_reminders`, `send_informal_30day`). Nu e nevoie să schimbăm dacă cron rulează zilnic.

---

## 5) Templates email

| Cerință | Status | Detalii |
|--------|--------|---------|
| Template HTML email + fallback text | ❌ | Toate emailurile sunt doar plain text. |

---

## Rezumat: ce e făcut vs ce lipsește

**Deja implementat (sau echivalent):**  
- Wishlist în DB, buton Te plac, redirect login și return, badge A0, pagină `/wishlist/` cu remove.  
- Reminder 72h (comandă), email la adopție (signal), email la 30 zile (comandă).  
- Fără schimbări de layout HOME / filtre Animale.

**De făcut / de modificat dacă vrei 100% conform spec ChatGPT:**  
1. **Opt-in email:** câmp `email_opt_in_wishlist`, checkbox la signup + în setări cont; trimite wishlist/30d doar dacă e True.  
2. **Anti-spam:** `last_wishlist_email_at` pe user/profile; max 1 email wishlist la 7 zile (cu excepție pentru emailul „adoptat”).  
3. **Unsubscribe:** view + URL + link în fiecare email wishlist.  
4. **Pagină wishlist:** opțional să afișezi și animalele adoptate cu badge de status.  
5. **Email adoptat:** adăugare 3 animale recomandate (același tip, mărime, vârstă) în corpul emailului.  
6. **Email 30 zile:** opțional refăcut ca „Încă îți cauți prietenul perfect?” + 4–6 recommended pets, pentru useri cu prima adăugare wishlist ≥ 30 zile.  
7. **Templates:** HTML (+ text) pentru emailurile wishlist.  
8. **URL:** alias `/my-wishlist/` → `/wishlist/` dacă vrei exact path-ul din spec.

Dacă vrei, următorul pas poate fi: implementare opt-in + unsubscribe + limită 7 zile (punctele 1–3), apoi restul la cerere.
