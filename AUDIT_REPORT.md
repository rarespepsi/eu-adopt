# Full Project Audit Report (Post-Cleanup)

**Date:** March 2026  
**Scope:** Verify only functional code remains active; list active files, duplicates, and unused items.  
**Rules applied:** No files modified or moved; report only.

---

## 1. Templates

### 1.1 Templates that are still rendered by Django

| View | URL name(s) | Template rendered |
|------|-------------|-------------------|
| `home_view` | `home`, `servicii`, `transport`, `shop`, `login`, `logout`, `register`, `contact`, `termeni`, `site_search`, `analiza`, `wishlist`, `my_wishlist`, `cont`, `cont_profil` | **anunturi/home_v2.html** (when not `pets_all`) |
| `home_view` | `pets_all` | **anunturi/pt.html** |
| `dog_profile_view` | `pets_single` | **anunturi/pets-single.html** |

**Effectively rendered templates (3):**
- `templates/anunturi/home_v2.html`
- `templates/anunturi/pt.html`
- `templates/anunturi/pets-single.html`

**Templates used via `extends` or `include` (not rendered directly):**
- `templates/base.html` (extended by home_v2, pt)
- `templates/components/navbar_a0.html` (included by base, pets-single)
- `templates/components/sidebar_left.html` (included by base)
- `templates/components/sidebar_right.html` (included by base)
- `templates/components/login_required_modal.html` (included by base, pets-single)
- `templates/anunturi/includes/dog_card.html` (included by home_v2)
- `templates/anunturi/includes/pt_p2_card.html` (included by pt)

### 1.2 Duplicated includes

- **No duplicated includes** in the active tree. Each of `navbar_a0.html`, `sidebar_left.html`, `sidebar_right.html`, `login_required_modal.html` is included from one or two places (base and/or pets-single), which is intended reuse, not duplication.
- `pt_p2_card.html` is included twice in pt.html (viewport + rest loop); same template, different context — not a structural duplicate.

### 1.3 Templates still present but never used

| Template | Reason |
|----------|--------|
| **templates/anunturi/analiza-animale.html** | Not rendered by any view; not included by any active template. |
| **templates/anunturi/includes/harta_judete.html** | Never included by any template (active or archived). |
| **templates/components/sidebar_box.html** | Never included; sidebars use class `sidebar-box` in markup, not this partial. |

All other non-archived templates are either rendered or included as above.

---

## 2. CSS

### 2.1 CSS files referenced by active templates

| Source | CSS files loaded |
|--------|------------------|
| **base.html** (used by home_v2, pt) | `style.css`, `navbar-a0-secured.css`, `pet-images-common.css` |
| **home_v2.html** (block extra_css) | `home_v2.css` |
| **pt.html** (block extra_css) | `pt-v2.css` |
| **pets-single.html** (standalone) | `style.css`, `navbar-a0-secured.css`, `pet-images-common.css`, `includes/js/flexslider.css`, `includes/fancybox/jquery.fancybox.css` |

**Active CSS list (referenced by active templates):**
- `static/css/style.css`
- `static/css/navbar-a0-secured.css`
- `static/css/pet-images-common.css`
- `static/css/home_v2.css`
- `static/css/pt-v2.css`
- `static/includes/js/flexslider.css`
- `static/includes/fancybox/jquery.fancybox.css`
- `static/includes/fancybox/helpers/jquery.fancybox-thumbs.css` (if loaded by fancybox)
- `static/includes/fancybox/helpers/jquery.fancybox-buttons.css` (if loaded by fancybox)

### 2.2 Duplicated / redefined selectors

- **Same selector, multiple files (intended cascade):**  
  `body.page-home-v2`, `#A2`, `body.page-home-v2 #A2` appear in **home_v2.css**, **pet-images-common.css**, and **navbar-a0-secured.css** with different properties. This is normal scoping, not erroneous duplication.
- **style.css:** Large file (~800+ rule blocks). No automated full duplicate-selector scan was run; manual review or a dedicated CSS lint tool would be needed to find exact duplicate selector blocks.
- **No conflicting duplicate** of the removed `.pt-p2-20grid` type was found; grid 4×3 is defined in `.pt-p2-viewport` (pt-v2.css) and in home_v2 for `#A2 .A2-casete-wrap`.

### 2.3 CSS files no longer referenced by any template

All of these are in **static/css/_archive/** and are not linked from any active template:

- `static/css/_archive/transport.css`
- `static/css/_archive/auth-pages.css`
- `static/css/_archive/pets-all-debug.css`
- `static/css/_archive/prietenul-tau-v2.css`
- `static/css/_archive/scales-overlay.css`

No unreferenced CSS remains in the **active** `static/css/` folder (outside _archive).

---

## 3. JavaScript

### 3.1 JS files actually loaded by templates

- **base.html:** No `<script src="...">` in the base file; `extra_js` block is optional.
- **home_v2.html:** Only inline script in `{% block extra_js %}` (quote rotation). **No external JS file.**
- **pt.html:** No scripts; no `extra_js` block. **No external JS file.**
- **pets-single.html:** Only one `<script>` block, inline (form confirmation, copy link, visited pets). **No external JS file** is referenced in the template.

**Conclusion:** **No external JavaScript files are loaded** by any of the three active templates. Flexslider and Fancybox CSS are loaded on pets-single, but no corresponding `.js` (e.g. jquery, flexslider, fancybox) is linked there; gallery behavior may rely on inline or missing JS.

### 3.2 Unused JS files (not referenced by any template)

All of these are in **static/js/_archive/** or **static/includes/js/_archive/** and are not referenced by any active template:

- `static/js/_archive/measure-home-layout.js`
- `static/js/_archive/ro-location.js`
- `static/js/_archive/auth-form-errors.js`
- `static/includes/js/_archive/rescue.js`
- `static/includes/js/_archive/jquery.sticky.js`
- `static/includes/js/_archive/jquery.mobilemenu.js`

**Still in active folders (never linked by active templates):**
- `static/sw.js` (service worker; may be registered by other code or not used)
- `static/includes/js/jquery-1.11.1.min.js`
- `static/includes/js/jquery.flexslider-min.js`
- `static/includes/fancybox/jquery.fancybox.js`
- `static/includes/fancybox/jquery.fancybox.pack.js`
- `static/includes/fancybox/helpers/jquery.fancybox-thumbs.js`
- `static/includes/fancybox/helpers/jquery.fancybox-media.js`
- `static/includes/fancybox/helpers/jquery.fancybox-buttons.js`

These are **unused by the current templates**; they were likely used by archived templates (e.g. contact, termeni, registration). If pets-single is supposed to have a working gallery/lightbox, it may need to link jQuery + Fancybox (and/or Flexslider) JS.

---

## 4. Django views and URLs

### 4.1 All active routes

| Path | View | URL name |
|------|------|----------|
| `/` | home_view | home |
| `/pets/` | home_view | pets_all |
| `/pets/<int:pk>/` | dog_profile_view | pets_single |
| `/servicii/` | home_view | servicii |
| `/transport/` | home_view | transport |
| `/shop/` | home_view | shop |
| `/login/` | home_view | login |
| `/logout/` | home_view | logout |
| `/register/` | home_view | register |
| `/contact/` | home_view | contact |
| `/termeni/` | home_view | termeni |
| `/search/` | home_view | site_search |
| `/analiza/` | home_view | analiza |
| `/wishlist/` | home_view | wishlist |
| `/my-wishlist/` | home_view | my_wishlist |
| `/cont/` | home_view | cont |
| `/profil/` | home_view | cont_profil |
| `/admin/` | Django admin | — |

Root URLconf: `euadopt_final/urls.py` includes `home.urls`.

### 4.2 Which template each view renders

| View | Renders | When |
|------|--------|------|
| **home_view** | **anunturi/pt.html** | `url_name == "pets_all"` (and no `?go=` redirect) |
| **home_view** | **anunturi/home_v2.html** | All other URL names (home, servicii, transport, etc.) |
| **dog_profile_view** | **anunturi/pets-single.html** | Always (for `/pets/<pk>/`) |

### 4.3 Views that are never used

- **All defined views are used.** Only two views exist: `home_view` and `dog_profile_view`; both are wired in `home.urls` and are hit by the routes above.
- There is no view that points to archived templates (e.g. no view renders `servicii.html`, `transport.html`, or any registration template); those URLs all serve `home_v2.html` or `pt.html`.

---

## 5. Project structure

### 5.1 Confirmation: removed files were moved to _archive

- **templates/_archive/**  
  - Contains 46 HTML files (anunturi, registration, components, animals, maintenance).  
  - README.md states these templates are not rendered by any view.

- **static/css/_archive/**  
  - transport.css, auth-pages.css, pets-all-debug.css, prietenul-tau-v2.css, scales-overlay.css.  
  - README.md states they are not loaded by active templates.

- **static/js/_archive/**  
  - measure-home-layout.js, ro-location.js, auth-form-errors.js.  
  - README.md describes them as previously used by archived templates.

- **static/includes/js/_archive/**  
  - rescue.js, jquery.sticky.js, jquery.mobilemenu.js.

No active template or view references anything inside _archive.

### 5.2 Confirmation: active pages (HOME and PT) still work

- **HOME**  
  - Route: `/` → `home_view` (name `home`) → `render(..., "anunturi/home_v2.html", ...)`.  
  - home_v2 extends base.html, loads style.css, navbar-a0-secured.css, pet-images-common.css, home_v2.css.  
  - base includes navbar_a0, sidebar_left, sidebar_right, login_required_modal.  
  - **Conclusion:** Template and asset chain are consistent; HOME is expected to work.

- **PT (Prietenul tău)**  
  - Route: `/pets/` → `home_view` (name `pets_all`) → `render(..., "anunturi/pt.html", ...)` with `p2_pets` / `p2_pets_rest`.  
  - pt extends base.html, adds pt-v2.css.  
  - **Conclusion:** Template and asset chain are consistent; PT is expected to work.

- **pets-single**  
  - Route: `/pets/<pk>/` → `dog_profile_view` → `render(..., "anunturi/pets-single.html", ...)`.  
  - Standalone template; loads style, navbar, pet-images-common, flexslider.css, fancybox.css; no external JS.  
  - **Conclusion:** Page should render; gallery/lightbox may be non-functional if it depends on Fancybox/Flexslider JS.

---

## Summary

### Active functional files (in use)

- **Templates:** base.html, home_v2.html, pt.html, pets-single.html, navbar_a0.html, sidebar_left.html, sidebar_right.html, login_required_modal.html, dog_card.html, pt_p2_card.html.
- **CSS:** style.css, navbar-a0-secured.css, pet-images-common.css, home_v2.css, pt-v2.css, flexslider.css, fancybox.css (and helpers if used).
- **JS:** None currently loaded by templates (only inline scripts).
- **Views/URLs:** home_view and dog_profile_view; all 17 routes in home.urls are active.

### Duplicates still present

- **Templates:** No structural duplication of includes; pt_p2_card included twice in pt with different context is intentional.
- **CSS:** Same selectors (e.g. `body.page-home-v2`, `#A2`) appear in several files by design (cascade/scoping). No duplicate *rule blocks* were automatically detected; style.css would need a dedicated audit for that.
- **JS:** N/A (no external JS in use).

### Unused files still remaining (outside _archive)

- **Templates:**  
  - `templates/anunturi/analiza-animale.html`  
  - `templates/anunturi/includes/harta_judete.html`  
  - `templates/components/sidebar_box.html`
- **JS (in active static folders):**  
  - sw.js; jquery-1.11.1.min.js; jquery.flexslider-min.js; fancybox JS set (jquery.fancybox.js, .pack.js, helpers). Not linked by any active template.

---

*End of audit report. No files were modified or moved.*
