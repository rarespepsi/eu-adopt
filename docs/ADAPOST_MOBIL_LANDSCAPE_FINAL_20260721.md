# Fișă adăpost — mobil landscape touch (FINAL sesiune 21 iul 2026)

**Pagină:** `/adaposturi/<slug>/` · **Fișier:** `templates/anunturi/adapost_detail.html` (`extra_css_after` + script la final).

**Media query:**

```css
@media (orientation: landscape) and (hover: none) and (pointer: coarse) and (max-height: 599px)
```

(`max-height: 599` = **nu tabletă**; fără `max-width: 767` = telefoane late în landscape, ex. iPhone.)

## Layout

| Zonă | Comportament |
|------|----------------|
| **Înapoi + PET în site** | Rând 1; **nu fixe** — scroll pagină, dispar sub navbar |
| **4 casete** | Grid `repeat(4, 1fr)`: adăpost + 3 promo **alăturate** (promo `display: contents`) |
| **Câini** | Grilă 4 col, scroll **pagină** (fără `overflow` intern pe `.adp-det__pets-scroll`) |

## Navbar / bandă goală

- Cauză: `body { --nav-height: clamp(48px,10vw,64px) }` vs A0 compact **34px** landscape.
- Fix: CSS `--nav-height: 34px` + **`adpSyncNavPadding()`** măsoară `#A0` și setează `padding-top` pe `#main_content`.

## Tabletă

- **Nu** amesteca: tablet landscape = `min-height: 600px` (regulă separată în același HTML).

## Live

Commit **`3f3fa91`** (Hetzner).

## Înghețare

**`1977` + OK** pentru orice editare.
