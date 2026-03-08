# EU-Adopt Project – Structure Reference

**Proiect de lucru: doar `euadopt_final/`.** Nu modifica proiectul vechi (fișiere din adoptapet_pro în afara folderului euadopt_final). Toate modificările se fac aici.

**Use only this structure. Do not suggest old layouts or alternative structures.**

## Development rules

1. **Keep the current project structure.** Do not redesign layout or architecture.
2. **HOME layout is frozen** – must not be modified (see below).
3. **A2** displays exactly **12 dogs** in a grid.
4. **Same 12 dogs** everywhere: Home, Prietenul tău, Dog profiles, Wishlist testing, Adoption flow.
5. **Dog card** must be reusable everywhere (one component).
6. **Do not invent** alternative layouts or new demo structures. Only extend the existing system.
7. **Modify the smallest possible amount of code.** Wait for instructions before generating large code blocks.

## Modificări home / layout – parolă obligatorie

**Orice modificare în app-ul `home`** (un punct, o virgulă, o linie – orice) **sau de layout** (grid, poziții, structură A0–A6) se face **doar cu aprobarea titularului, cu parola** de autorizare. Fără parolă – nu se modifică nimic în home și nici layout-ul.

---

## HOME page layout (FROZEN)

**Checkpoint:** `HOME_LAYOUT_LOCKED.md`

The homepage section structure and layout are **locked**. Future changes are allowed **only inside the content of the sections**, not in the layout itself.

- **Do not** rename sections (A0, A1, A2, A3, A4, A5, A6).
- **Do not** change grid sizes (e.g. A2 stays 4×3).
- **Do not** change column structure (A5 | center A1,A2,A3 | A6).

| Slot | Role |
|------|------|
| **A0** | Navbar |
| **A1** | Hero banner |
| **A2** | Dogs grid (4×3) |
| **A3** | Mission / counters bar |
| **A4** | Footer |
| **A5** | Left sidebar (3 slots) |
| **A6** | Right sidebar (3 slots) |

Layout: **A0** top → **A5 | A1, A2, A3 | A6** (3 columns) → **A4** bottom.

---

## P2 layout – Prietenul Tău grid (FROZEN)

**Checkpoint:** `P2_LAYOUT_LOCKED.md`

The P2 grid structure is **locked**. Future changes are allowed **only inside cell content**, not in the layout.

- **4 columns**, **3 equal visible rows**, **internal scroll**, **equal cell size**.
- **Do not** change column count, row count, scroll behavior, or grid/cell layout.
- **Only** content inside P2 cells may change.

---

## Demo dogs (development)

- **Fixed set of 12 demo dogs** – reused across the whole platform.
- They appear in: **Home**, **Prietenul tău**, **Dog profiles**, **Wishlist testing**, **Adoption flow**.
- **Do not generate new demo dogs.** Use the same 12 everywhere (one source of truth: fixture, constant IDs, or single query).

---

## Dog card (reusable)

The **dog card** component is shared across:

- Home (A2 grid)
- Prietenul tău
- Dog profile page
- Wishlist
- Adoption flow

One card structure, consistent styling and behaviour everywhere.

---

*Last updated: March 2026*
