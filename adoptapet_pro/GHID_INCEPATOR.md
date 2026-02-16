# Ghid pentru începători – de la zero

Acest document explică, de la început, ce face fiecare program și cum lucrezi cu el în proiectul EU Adopt.

---

## 1. Python

**Ce este:** Limbajul de programare în care e scrisă aplicația Django.

**De ce îl folosim:** Pentru serverul web, logica din spatele site-ului (formulare, baze de date, etc.).

**Cum lucrezi cu el:**
- Nu trebuie să scrii Python de la început – codul există deja.
- Pentru comenzi în terminal, rulezi: `python nume_script.py` sau `python manage.py comanda`
- Exemple: `python manage.py runserver` (pornește site-ul local), `python manage.py migrate` (actualizează baza de date)

**Unde să înveți mai mult:** [python.org – tutorial oficial](https://docs.python.org/3/tutorial/)

---

## 2. Cursor (IDE-ul)

**Ce este:** Editorul în care editezi codul – ca un Word pentru programatori.

**De ce îl folosim:** Pentru a modifica fișiere, a vedea structura proiectului, a rula comenzi în terminal.

**Cum lucrezi cu el:**
- **Stânga:** panoul cu fișiere (File Explorer) – click pe un fișier ca să-l deschizi.
- **Centru:** zona unde editezi codul.
- **Jos:** terminalul – aici rulezi comenzi (`python`, `git`, etc.).
- **Ctrl+S** – salvează fișierul.
- **Ctrl+Shift+P** – deschide paleta de comenzi (caută orice funcție).

**Început rapid:** Deschide un proiect (File → Open Folder), apoi navighează prin fișiere în stânga.

---

## 3. Terminal (PowerShell / CMD)

**Ce este:** Fereastra unde scrii comenzi text în loc să dai click pe butoane.

**De ce îl folosim:** Pentru comenzi care nu au interfață grafică: `python`, `git`, `pip`, etc.

**Comenzi de bază:**
| Comandă | Ce face |
|---------|---------|
| `cd c:\calea\la\folder` | Intră într-un folder |
| `dir` (sau `ls`) | Afișează fișierele din folderul curent |
| `python --version` | Arată versiunea de Python instalată |
| `pip install nume_pachet` | Instalează un pachet Python |

**Regulă:** Calea trebuie să fie exactă. Ex: `cd c:\Users\USER\Desktop\adoptapet_pro` pentru a intra în proiect.

---

## 4. Git

**Ce este:** Sistem de control al versiunilor – ține istoricul modificărilor și permite colaborarea.

**Ce face pentru tine:**
- Salvează „snapshot-uri” ale proiectului (commit-uri).
- Te lasă să revii la versiuni anterioare.
- Sincronizează codul cu GitHub și cu Render.

**Comenzi de bază:**
| Comandă | Ce face |
|---------|---------|
| `git status` | Arată ce fișiere au fost modificate |
| `git add nume_fisier` | Pregătește fișierul pentru commit |
| `git add .` | Pregătește toate modificările |
| `git commit -m "mesaj"` | Salvează modificările cu un mesaj |
| `git push origin main` | Trimite modificările pe GitHub |

**Flux normal:** Modifici cod → `git add` → `git commit` → `git push`

**Dacă Git nu e recunoscut în terminal:** Folosește calea completă:
```
"C:\Program Files\Git\bin\git.exe" status
```

---

## 5. GitHub

**Ce este:** Serviciu online unde stochezi codul (repository = „repo”).

**De ce îl folosim:** Păstrare cod în cloud, partajare, și ca sursă pentru deploy pe Render.

**Cum lucrezi cu el:**
- **În browser:** Mergi pe github.com, te loghezi, deschizi repo-ul (ex: rarespepsi/eu-adopt).
- **Prin Git:** `git push` trimite codul local pe GitHub; `git pull` aduce modificări de pe GitHub local.

**Nu editezi direct codul pe GitHub** (de obicei) – editezi local în Cursor și apoi faci push.

---

## 6. Django

**Ce este:** Framework Python pentru site-uri web – oferă structură pentru URL-uri, baze de date, template-uri.

**Structura proiectului (simplificat):**
```
adoptapet_pro/
├── manage.py          # Comanda principală Django
├── platforma/         # Setări generale (settings, urls principale)
├── anunturi/          # Aplicația principală (models, views, urls)
└── templates/         # Fișiere HTML
```

**Comenzi utile:**
| Comandă | Ce face |
|---------|---------|
| `python manage.py runserver` | Pornește site-ul local (http://127.0.0.1:8000) |
| `python manage.py migrate` | Aplică migrări la baza de date |
| `python manage.py makemigrations` | Creează migrări pentru modele noi/modificate |

**Flux:** Editezi views, templates, urls → salvezi → reîmprospătezi browserul (site-ul local se reîncarcă automat).

---

## 7. Render

**Ce este:** Platformă de hosting – rulează site-ul tău pe internet.

**Cum funcționează:**
1. Render e conectat la GitHub.
2. La fiecare `git push` pe branch-ul `main`, Render face deploy automat.
3. Site-ul live e la: https://eu-adopt.onrender.com

**Ce faci tu:**
- Mergi pe [dashboard.render.com](https://dashboard.render.com).
- Vezi statusul deploy-urilor (Events, Logs).
- Dacă ceva nu merge, verifici logurile de eroare.

**Nu editezi codul pe Render** – totul vine din GitHub după push.

---

## Fluxul complet: de la modificare la site live

1. **Deschizi proiectul** în Cursor (File → Open Folder → adoptapet_pro).
2. **Modifici** fișierele necesare (ex: views.py, templates).
3. **Salvezi** (Ctrl+S).
4. **Testezi local** (opțional): `python manage.py runserver` → deschizi http://127.0.0.1:8000.
5. **Commit:** `git add .` → `git commit -m "Descriere modificare"`.
6. **Push:** `git push origin main`.
7. **Render** ia codul de pe GitHub și face deploy (2–5 min).
8. **Verifici** site-ul live: https://eu-adopt.onrender.com.

---

## Recomandare pentru învățare

**Ordinea logică:**
1. Cursor + Terminal (navigare, comenzi simple).
2. Python (sintaxă de bază, ce e o funcție, o clasă).
3. Django (ce e un view, un template, un URL).
4. Git (status, add, commit, push).
5. GitHub + Render (cum se leagă totul).

**Resurse:**
- [Python pentru începători (în română)](https://www.learnpython.org/ro/)
- [Django Official Tutorial](https://docs.djangoproject.com/en/stable/intro/tutorial01/)
- [Git – документация (Simplificat)](https://githowto.com/)

---

*Acest ghid e în proiectul tău – poți reveni la el oricând.*
