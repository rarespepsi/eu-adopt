# ⚠️ FIȘIER VECHI – CONȚINUT CENTRALIZAT

**📚 Acest fișier a fost centralizat în `DOCUMENTATIE_CENTRALIZATA.md`**  
**Nu mai actualiza acest fișier – folosește fișierul centralizat pentru a evita duplicarea informațiilor.**

---

# EU-ADOPT — GLOBAL UI RULES

## Reguli fundamentale pentru interfața site-ului

### 1. Sistem de Slot-uri (A0–A17)
- Website folosește sistemul de **SLOT-uri** identificate **A0–A17**.
- Fiecare slot poate fi controlat individual prin ID (A6, A9, etc.).

### 2. Structura Layout-ului
- **Structura layout-ului NU trebuie schimbată** decât dacă este explicit solicitat.
- Nu modifica pozițiile slot-urilor, coloanele sau structura grid-ului.

### 3. Tipuri de Conținut în Slot-uri
Toate slot-urile trebuie să suporte:
- **Imagine**
- **Video**
- **Animație**

### 4. Sidebar-uri Fixe
- **Sidebar-urile stânga și dreapta sunt FIXE (freeze)**.
- Nu se deplasează la scroll.
- Doar conținutul din **CENTRU** se scroll-ează.

### 5. Scroll Behavior
- **Doar conținutul CENTRAL** se scroll-ează.
- Sidebar-urile rămân fixe în poziție.

### 6. Înălțimi Standardizate pentru Sidebar-uri
- Slot-urile din sidebar-uri trebuie să aibă **înălțimi standardizate**.
- Asigură consistență vizuală.

### 7. Pagina HOME
- **Pagina HOME este o pagină de CĂUTARE / CATALOG**, nu o pagină informațională.
- Focus pe funcționalitate de căutare și listare animale.

### 8. Text în Slot-uri
- **Textul din slot-uri trebuie să fie scurt**.
- **Maximum 2–3 linii** de text per slot.
- Evită texte lungi care afectează layout-ul.

### 9. Reclame
- **Reclamele NU trebuie să împingă sau să redimensioneze conținutul central**.
- Reclamele trebuie integrate fără a afecta layout-ul principal.

### 10. Prioritate: Stabilitate Design
- **Stabilitatea design-ului are prioritate** față de efecte vizuale.
- Evită animații sau efecte care pot afecta performanța sau experiența utilizatorului.

### 11. Control Individual al Slot-urilor
- Slot-urile pot fi controlate individual prin ID (A6, A9, etc.).
- Fiecare slot poate avea propriile setări și conținut.

### 12. Modul VIP Stacked
- **Modul VIP stacked trebuie să fie suportat** fără schimbări de layout.
- Nu trebuie să apară shift-uri de layout când se activează modul VIP.

### 13. Responsive Design
- **Comportamentul responsive trebuie păstrat** pe ecrane mai mici.
- Site-ul trebuie să funcționeze corect pe mobile și tabletă.

---

## Note de Implementare

- Aceste reguli se aplică la **toate paginile** site-ului.
- Orice modificare care contravine acestor reguli trebuie discutată înainte de implementare.
- Prioritatea este **stabilitatea și funcționalitatea**, nu efectele vizuale.

---

*Document creat: februarie 2025*
