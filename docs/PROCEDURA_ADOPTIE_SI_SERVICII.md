# Procedură: Adopție încheiată → Servicii (carduri parteneri)

*Notat ca referință pentru implementare ulterioară. Descrie fluxul de la „adopție finalizată” la alegerea serviciilor parteneri și trimiterea mailurilor.*

---

## 1. Când se consideră adopția „închisă / realizată”

- Adoptatorul a ajuns fie la adăpost, fie a primit animalul acasă → adopția este **realizată**.
- **Cum o înregistrăm:** Adăpostul / ONG-ul încheie adopția din pagina lui prin click pe **„Adopție finalizată”** (sau numele exact al butonului).

---

## 2. Flux adoptator: Adopt → pagina carduri (regulă județ)

1. Adoptatorul caută pe site, găsește un animal și apasă **„Adopt”** (trimite cererea spre aprobare la adăpost).
2. **Imediat după ce apasă Adopt** este **transferat direct pe pagina carduri** (Servicii), cu o regulă obligatorie:
   - **Dacă în județul adoptatorului nu este niciun card/partener** → **nu** se face transfer automat (rămâne pe fluxul normal, fără pagină carduri).
   - **Dacă în județ există cel puțin 1 serviciu/partener** → **da**, este transferat automat pe pagina carduri.
3. Pe pagina carduri vede cele **trei categorii** (Cabinete veterinare, Magazine specializate, Saloane cosmetica Vet) și **alege** (bifează) cardurile dorite (câte unul per categorie, dacă vrea).
4. Este **instiintat** pe pagină: aceste carduri **se activează** după ce adopția este **aprobată de adăpost/ONG** și **dusă la îndeplinire**; va primi pe mail datele cardurilor bifate de el.
5. **O dată ce dă Accept** (confirmă alegerea) → **nu mai poate modifica** cardurile și nici să aleagă altele. Alegerea este blocată.
6. **Varianta ideală:** adoptatorul alege imediat după ce a dat Adopt. Esențial: primește clar mesajul că **cardurile se activează după ce adopția a fost confirmată de adăpost/ONG**.

---

## 3. Cardurile pe Servicii

- Fiecare **card** conține:
  - **Nume** (prestator / serviciu).
  - **Badge:** „Partener Eu-adopt”.
  - **Mic avantaj:** discount, serviciu, produs etc.
- Adoptatorul poate **alege câte unul din fiecare categorie** (deci 1, 2 sau 3 servicii).
- **Dacă nu alege** în niciuna din categorii: trimitem **zero** și finalizăm doar cu ce a ales (poate 0, 1, 2 sau 3).

---

## 4. Mesaj către adoptator (pe pagina carduri)

Pe pagina carduri (Servicii) adoptatorul primește mesajul că:

- Aceste carduri **se activează** după ce adopția este **aprobată de adăpost/ONG** și **dusă la îndeplinire**.
- Va primi **pe mail** datele cardurilor pe care le-a bifat (dacă adopția este confirmată și finalizată).
- (Opțional, text de tip: „Pentru bunătatea ta pentru acest câțel/pisică, oameni cu suflet mare au ales să te ajute!” etc.)

---

## 5. Când adăpostul apasă „Adopție finalizată” – notificare către adoptator

- **Automat** trimitem către adoptator (pe canalul ales în fișa user) informațiile:
  - Cele **1, 2 sau 3 servicii alese**.
  - **Toate informațiile** necesare pentru a ajunge la prestator (adresă, telefon, program etc.).
  - Un **cod** generat de noi: de obicei **numele celui care oferă serviciul + 2–3 cifre** (ex. „CabinetVet12”, „MaxiPet07”).
- **Canalul de notificare** depinde de ce bifează adoptatorul în **fișa user**: **Email**, **SMS** sau **WhatsApp** (trimitem pe canalul / canalele bifate).

---

## 6. Mail către prestatori (cei 1, 2 sau 3 parteneri)

- La aceeași confirmare **„Adopție finalizată”**, cei care oferă servicii (discount / produs) primesc un **mail** cu:
  - **Datele adoptatorului**.
  - **Codul PIN** trimis de noi (pentru verificare formală la prezentare).

---

## 7. Rezumat pentru adoptator

- Adoptatorul primește (pe **email**, **SMS** sau **WhatsApp**, după preferințele din fișa user) **toate datele legate de prestator**: adresă, telefon, program etc., plus **codul** pentru a se prezenta la partener.

---

## 8. Fișa user – preferințe notificare (de adăugat)

- În **fișa utilizatorului** (profil / setări cont) trebuie puse opțiunile pentru **primit notificări** (datele cardurilor după finalizare adopție) pe:
  - **Email**
  - **SMS**
  - **WhatsApp**
- Utilizatorul bifează ce preferă (unul sau mai multe). La „Adopție finalizată” trimitem informațiile pe canalul / canalele bifate.
- **Implementare:** câmpuri în modelul de profil (ex. `UserProfile`: `notify_by_email`, `notify_by_sms`, `notify_by_whatsapp` sau un câmp tip preferință) și în formularul / pagina de editare profil.

---

## 9. Note tehnice (de implementat)

- **După click pe Adopt:** verificare județ adoptator; dacă ≥1 partener în județ → redirect la pagina carduri (Servicii); altfel nu.
- **Pagina carduri:** alegere 0–1 din fiecare categorie; buton **Accept** → salvare și **blocare** alegeri (nu mai poate modifica).
- **Conținut carduri:** momentan poze și texte de probă; când există colaboratori reali, fiecare card va folosi **poza și datele din fișa partenerului** (profil/fiche colaborator).
- Mesaj pe pagină: cardurile se activează după aprobare + finalizare adopție; datele le primește pe email / SMS / WhatsApp (după fișa user).
- **Buton adăpost/ONG:** „Adopție finalizată” → la click: notificare către adoptator (email/SMS/WhatsApp după preferințe) cu servicii alese + date prestatori + cod; mail către fiecare prestator ales (date adoptator + cod PIN).
- Generare **cod**: nume prestator + 2–3 cifre.

---

*Document creat: februarie 2026 – procedură adoptie + servicii parteneri.*
