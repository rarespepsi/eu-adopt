# Raport punctual – poze-problemă A2 (3–4 câini)

**Data:** martie 2026  
**Scop:** Verificare punctuală fără modificare CSS. Pentru fiecare poză-problemă: nume câine, URL imagine, problema în fișier sau în mapping.

---

## 1. Jack (pk=107) – Slot A2.1

| Câmp | Valoare |
|------|--------|
| **Nume câine** | Jack |
| **URL imagine** | `/static/images/pets/charlie-275x275.jpg` |
| **Sursă DB** | `imagine_fallback` (static) |
| **Cale fișier** | `static/images/pets/charlie-275x275.jpg` (sau staticfiles după collectstatic) |

**Verificare fișier:**
- Dimensiuni: 275×275 px
- Raport aspect: 1:1 (pătrat), nu 4:3
- Margini albe (estimare): nu
- Canvas gol / subiect foarte mic: nu

**Problema:**  
- **Mapping:** Câinele nu are câmpul `imagine` (upload) setat; folosește același `imagine_fallback` ca mulți alții → toți arată aceeași poză Charlie.  
- **Fișier:** Imaginea este pătrată (1:1). În casetă 4:3, `background-size: cover` o taie pe verticală sau orizontală; nu „prost crop” în fișier, dar aspectul fișierului nu este 4:3.

**Concluzie:** Problema este în **mapping** (lipsă poză proprie) și în **alegerea fișierului fallback** (pătrat, nu 4:3).

---

## 2. Lucy (pk=106) – Slot A2.2

| Câmp | Valoare |
|------|--------|
| **Nume câine** | Lucy |
| **URL imagine** | `/static/images/pets/charlie-275x275.jpg` |
| **Sursă DB** | `imagine_fallback` (static) |

**Verificare fișier:** La fel ca Jack – 275×275, aspect 1:1, fără margini albe evidente.

**Problema:**  
- **Mapping:** Același fallback ca Jack/Buddy/Milo → nu pointează la o imagine specifică Lucy.  
- **Fișier:** Același fișier Charlie, aspect pătrat.

**Concluzie:** Problema este în **mapping** (toți pun la același static); fișierul nu este „greșit”, dar e partajat și nu 4:3.

---

## 3. Buddy (pk=105) – Slot A2.3

| Câmp | Valoare |
|------|--------|
| **Nume câine** | Buddy |
| **URL imagine** | `/static/images/pets/charlie-275x275.jpg` |
| **Sursă DB** | `imagine_fallback` (static) |

**Problema:** Identică cu Jack/Lucy – **mapping** (același fallback), **fișier** același (aspect 1:1).

**Concluzie:** Problema este în **mapping**.

---

## 4. Milo (pk=104) – Slot A2.4

| Câmp | Valoare |
|------|--------|
| **Nume câine** | Milo |
| **URL imagine** | `/static/images/pets/charlie-275x275.jpg` |
| **Sursă DB** | `imagine_fallback` (static) |

**Problema:** La fel – **mapping** (fallback comun), **fișier** 275×275, 1:1.

**Concluzie:** Problema este în **mapping**.

---

## Rezumat

| # | Nume câine | URL imagine | Problema în fișier? | Problema în mapping? |
|---|------------|-------------|----------------------|----------------------|
| 1 | Jack  | `/static/images/pets/charlie-275x275.jpg` | Da (aspect 1:1, nu 4:3) | Da (același fallback pentru toți, fără poză upload) |
| 2 | Lucy  | `/static/images/pets/charlie-275x275.jpg` | Da (același fișier)     | Da (același fallback) |
| 3 | Buddy | `/static/images/pets/charlie-275x275.jpg` | Da (același fișier)     | Da (același fallback) |
| 4 | Milo  | `/static/images/pets/charlie-275x275.jpg` | Da (același fișier)     | Da (același fallback) |

**Concluzie generală:**  
- **Mapping:** Câinii folosesc doar `imagine_fallback` și toți pun la același fișier static; nu au `imagine` (upload) setat. Pentru poze „corecte” per câine trebuie fie upload pe fiecare, fie fallback-uri diferite (și preferabil 4:3).  
- **Fișier:** `charlie-275x275.jpg` este 275×275 (1:1). Nu are margini albe sau subiect foarte mic, dar raportul nu este 4:3; pentru casete A2 (4:3) un fișier 4:3 sau crop la upload reduce spațiile vizuale.

Raportul a fost generat cu: `python manage.py raport_poze_a2_problema`.
