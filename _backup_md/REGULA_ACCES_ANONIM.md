# Regulă: acces utilizatori NE-logați (anonimi)

## Ce poate face un vizitator fără cont

- poate naviga liber pe:
  - **Home**,
  - **Prietenul tău** (lista generală de animale),
  - **Servicii**,
  - **Transport**,
  - **Shop** (doar vitrina, fără cumpărare),
  - poate vedea butoanele din navbar: **MyPet, I Love, Intră** (nu vede **Analiza** – doar adminii o văd).

## Ce NU poate face fără să aibă cont

- nu poate:
  - **adopta un animal**,
  - **vedea fișa completă** a unui animal (date detaliate, contacte),
  - **trimite mesaje** către adăpost/ONG,
  - **cumpăra ceva** din Shop (finalizare comandă),
  - **folosi MyPet / I Love** pe bune (salvare animale, preferințe, statistici),
  - accesa zona **Analiza**.

## Comportament standard

- Dacă un utilizator NE-logat:
  - apasă **Analiza, MyPet, I Love, Logout** în navbar, sau
  - apasă pe acțiuni care cer cont (ex. „Adoptă”, „Vreau să știu mai mult”, „Cumpără”),
- atunci este redirecționat către:
  - **pagina de intrare / înregistrare** (login/signup),
  - cu un mesaj clar de tip: *„Ai nevoie de cont pentru a folosi această funcție.”*

## Implementare treptată

- Pasul 1: butoanele din navbar sunt **vizibile mereu**; pentru utilizatorii NE-logați duc către pagina de login / înregistrare.
- Pasul 2: la implementarea backend-ului pentru adopții, Shop și mesaje, se adaugă același tip de protecție (redirect la login când nu există user autentificat).

