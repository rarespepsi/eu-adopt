# Idei și taskuri amânate – reamintire la finalizare

*Document creat ca să-ți aduc aminte de taskurile și ideile discutate dar neimplementate încă. Când finalizăm aranjarea paginii / site-ul, revizuim acest fișier.*

---

## Taskuri memorate (de făcut ulterior)

1. **Reset date la lansare**  
   Când site-ul e gata de lansare: ștergere users, câini (animale) și alte date fictive adăugate pentru probe. Opțiuni: din Django Admin, sau un management command (ex. `clear_test_data`). *Nu se face acum.*

2. **Setare acces pe roluri (dacă e nevoie)**  
   - Administrator = acces la toate datele și toate paginile (ca acum).  
   - User de rând (PF, ONG etc.) = acces doar la anumite pagini; restul ascunse în meniu și protejate la view. *Se poate face când e nevoie; nu acum.*

3. **Modificare navbar pentru mobil**  
   Când ajungem la **finalul construcției paginii home**: adaptare navbar (A0) pentru mobil (ex. padding 7cm/6cm în px/em pe ecrane mici, meniu compact sau hamburger, fără scroll orizontal). *Amânat până la finalizarea layout-ului home.*

---

## Idei nepus în practică

- Afișare username în navbar pentru user logat (ex. „Bun venit, {{ user.username }}”) – discutat, opțional.
- Lista de corecturi numerotate – de stabilit; la „start modificări” se execută în ordine.
- Traseu (meniu / rute / flux) – de refăcut/stabilit la cerere.
- **Caseta sidebar (A6, A7, A8, A9, A10 sau A11)** – colaborare cu cabinetele veterinare din țară care sterilizează gratuit; posibilitate ca vizitatorul să contribuie la cauza sterilizării (informații + eventual donație/contribuție).
- Alte idei din conversații (ex. pagină Marketing, SUPERPOWER membri, etc.) – de revenit când stabilim prioritățile.

---

*Actualizat: februarie 2026. Revizuiește acest fișier când finalizezi aranjarea paginii.*

**Arhivă completă:** toate ideile, taskurile amânate și propunerile din proiect sunt trecute în revistă și arhivate în **`ARHIVA_IDEI_TASKURI_SI_PROPUNERI.md`**.
