# Email real cu Gmail – pas cu pas

Acest ghid te ajută să configurezi trimiterea de email din site (bun venit, adopții, etc.) folosind Gmail. Parola normală de Gmail **nu** funcționează – trebuie o **Parolă pentru aplicații**.

---

## Pasul 1: Verificare în 2 pași (obligatoriu)

1. Deschide în browser: **https://myaccount.google.com/security**
2. Conectează-te cu contul **contact.euadopt@gmail.com** (sau contul Gmail pe care vrei să îl folosești).
3. Găsește secțiunea **„Verificare în 2 pași”**.
4. Dacă este **Oprită** – apasă pe ea și **activeaz-o** (urmează pașii: număr de telefon, cod SMS).
5. Dacă este deja **Activată** – treci la Pasul 2.

Fără verificare în 2 pași, Google nu îți permite să creezi Parolă pentru aplicații.

---

## Pasul 2: Creează Parola pentru aplicații

1. Tot pe **https://myaccount.google.com/security**, scroll în jos până la **„Parole pentru aplicații”**.
2. Apasă pe **„Parole pentru aplicații”**.
3. Dacă îți cere parola contului Google, introdu-o.
4. La **„Selectează aplicația”** alege: **„Mail”**.
5. La **„Selectează dispozitivul”** alege: **„Calculator Windows”** (sau „Altul” și scrie „EU-Adopt”).
6. Apasă **„Generare”**.
7. Îți apare un **cod de 16 caractere** (ex: `abcd efgh ijkl mnop`), unele cu spațiu în mijloc.
8. **Copiază** acel cod (sau notează-l). Îl vei folosi în Pasul 3 – **fără spații** (ex: `abcdefghijklmnop`).

Nu închide fereastra până nu ai copiat codul; îl poți folosi de mai multe ori.

---

## Pasul 3: Adaugă parola în proiect (fișierul .env)

1. Deschide folderul proiectului: **adoptapet_pro** (acolo unde este `manage.py`).
2. Caută fișierul numit **`.env`**.
   - Dacă **există** – deschide-l cu Editor de text / Notepad / VS Code.
   - Dacă **nu există** – creează un fișier nou și salvează-l cu numele exact: **`.env`** (cu punct în față), în folderul **adoptapet_pro**.
3. În fișierul `.env` adaugă o linie nouă (sau completează dacă există deja):

   ```
   EMAIL_HOST_PASSWORD=abcdefghijklmnop
   ```

   Înlocuiește `abcdefghijklmnop` cu cele **16 caractere** de la Pasul 2, **fără spații și fără liniuțe**.

   Exemplu dacă Google ți-a dat: `abcd efgh ijkl mnop`  
   Scrii în .env:  
   `EMAIL_HOST_PASSWORD=abcdefghijklmnop`

4. Salvează fișierul și închide-l.

**Important:** Nu pune parola în niciun alt fișier (settings.py, etc.) și nu o pune pe internet. Doar în `.env` pe calculatorul tău (și pe server, dacă ai, prin variabile de mediu).

---

## Pasul 4: (Opțional) Schimbă adresa site-ului în mailuri

Dacă site-ul tău este de exemplu **https://pagina.eu**, poți seta în `.env`:

```
SITE_URL=https://pagina.eu
```

Atunci linkul „Te poți autentifica” din mail va duce la **https://pagina.eu/login/** în loc de eu-adopt.ro.  
Dacă nu pui nimic, se folosește implicit `https://eu-adopt.ro`.

---

## Pasul 5: Repornește serverul Django

- Dacă rulezi site-ul **pe calculator** (comanda `python manage.py runserver`):
  1. Oprește serverul (Ctrl+C în terminal).
  2. Pornește-l din nou: `python manage.py runserver`.

- Dacă rulezi site-ul **pe un server** (ex: Render):
  1. În panoul de control (Render) adaugă variabila de mediu: **EMAIL_HOST_PASSWORD** = cele 16 caractere (parola pentru aplicații).
  2. Fă **Redeploy** la aplicație.

După repornire, setările noi din `.env` sunt citite.

---

## Pasul 6: Verifică că emailul funcționează

1. Deschide un terminal în folderul **adoptapet_pro**.
2. Rulează:

   ```
   python manage.py verifica_email
   ```

   Ar trebui să vezi ceva de genul:
   - **EMAIL_BACKEND: ...smtp...** (nu „console”)
   - **DEFAULT_FROM_EMAIL: EU-Adopt &lt;contact.euadopt@gmail.com&gt;**

3. Pentru un **email de test** la propria ta adresă:

   ```
   python manage.py verifica_email --test --to=adresa-ta@gmail.com
   ```

   Înlocuiește `adresa-ta@gmail.com` cu un email la care poți verifica.  
   Dacă totul e configurat corect, primești mailul în inbox (verifică și în Spam).

---

## Rezumat

| Pas | Ce faci |
|-----|--------|
| 1   | Activezi Verificare în 2 pași la contul Gmail |
| 2   | Creezi „Parolă pentru aplicații” și copiezi cele 16 caractere |
| 3   | Pui în `.env` linia: `EMAIL_HOST_PASSWORD=cele16caractere` |
| 4   | (Opțional) Pui în `.env`: `SITE_URL=https://site-ul-tau.ro` |
| 5   | Repornești serverul (sau redeploy pe server) |
| 6   | Rulezi `python manage.py verifica_email` (și opțional `--test --to=...`) |

După acești pași, toate mailurile trimise de site (bun venit la cont nou, cereri adopție, etc.) vor pleca de la **contact.euadopt@gmail.com** și vor ajunge în inbox.

---

**Probleme frecvente**

- **„Username and Password not accepted”** – ai folosit parola normală de Gmail în loc de Parola pentru aplicații. Refă Pasul 2 și folosește doar cele 16 caractere.
- **Nu primesc mailul** – verifică Spam; asigură-te că ai repornit serverul după ce ai modificat `.env`.
- **.env nu e citit** – fișierul trebuie să se numească exact `.env` și să fie în același folder cu `manage.py`.
