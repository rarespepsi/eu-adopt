# Imagini – pagina Intra (login)

## Structură

| Folder / fișier | Rol |
|-----------------|-----|
| `backgrounds/` | Poze full-bleed pentru fundal (`background-size: cover`). Aici pui variantele noi (ex. `slide2.jpg`). |
| `slide1.png` | Fundal folosit acum în șablon (rădăcină `login/`); poți muta copii în `backgrounds/` când testezi alte imagini. |

## Convenții

- **Format:** PNG sau JPG/WebP; panoramic (≥ 16:9) merge bine cu `cover`.
- **Nume:** fără spații, ex. `login-hero-moody-01.jpg`.
- **Django static:** în template, `{% static 'images/login/backgrounds/nume-fisier.ext' %}`.

## Notă

După ce adaugi o poză nouă, în `templates/anunturi/login.html` (bloc `extra_css_after`) actualizezi `url(...)` spre fișierul din `backgrounds/` dacă vrei să o folosești live.
