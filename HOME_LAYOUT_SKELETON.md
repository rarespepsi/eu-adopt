# HOME LAYOUT SKELETON - FIXED STRUCTURE A0-A17

## Overview
This document describes the fixed skeleton layout for the HOME page using slots A0-A17.

## Non-negotiable Rules
1. **A0 and A1 are sticky (freeze) at the top** with ZERO gap between them
2. **Below A0+A1**, page is a **3-column layout**: left sidebar (freeze), center (scroll), right sidebar (freeze)
3. **Only the center column scrolls** (`overflow-y: auto`). Sidebars do NOT scroll.
4. **Remove any margins/paddings** causing vertical gaps between A0–A1–A2
5. **Use explicit IDs A0–A17** in DOM. No duplicates.

## Structure

### HTML Template Structure

```
<body class="page-home">
  <section id="main_wrap">
    <!-- A0 - Navbar (sticky top) -->
    <header id="A0" data-slot="A0">
      ...navbar content...
    </header>
    
    <!-- A1 - Strip (sticky below A0, zero gap) -->
    <div id="A1" data-slot="A1">
      ...strip content...
    </div>
    
    <!-- Main Content Wrapper -->
    <section id="main_content" class="wrapper">
      <div class="layout">
        <!-- Left Sidebar (FREEZE, NO SCROLL) -->
        <aside class="sidebar-left">
          <div id="A6" class="slot-container" data-slot="A6">...</div>
          <div id="A7" class="slot-container" data-slot="A7">...</div>
          <div id="A8" class="slot-container" data-slot="A8">...</div>
          <div id="A9" class="slot-container" data-slot="A9">...</div>
          <div id="A10" class="slot-container" data-slot="A10">...</div>
          <div id="A11" class="slot-container" data-slot="A11">...</div>
        </aside>
        
        <!-- Center Column (SCROLLABLE) -->
        <main class="main-content">
          <div class="container clearfix home_page_sections">
            <div id="A2" class="slot-container" data-slot="A2">...</div>
            <div id="A3" class="slot-container" data-slot="A3">...</div>
            <div id="A4" class="slot-container" data-slot="A4">...</div>
            <div id="A5" class="slot-container" data-slot="A5">...</div>
          </div>
        </main>
        
        <!-- Right Sidebar (FREEZE, NO SCROLL) -->
        <aside class="sidebar-right">
          <div id="A12" class="slot-container" data-slot="A12">...</div>
          <div id="A13" class="slot-container" data-slot="A13">...</div>
          <div id="A14" class="slot-container" data-slot="A14">...</div>
          <div id="A15" class="slot-container" data-slot="A15">...</div>
          <div id="A16" class="slot-container" data-slot="A16">...</div>
          <div id="A17" class="slot-container" data-slot="A17">...</div>
        </aside>
      </div>
    </section>
  </section>
</body>
```

## CSS Skeleton

The CSS skeleton is defined in `static/css/home-skeleton.css` and enforces:

### A0 (Navbar)
- `position: sticky; top: 0; z-index: 2000;`
- `height: 64px;` (compact)
- `width: 100%;`
- `margin: 0; padding: 0;`

### A1 (Strip)
- `position: sticky; top: 64px; z-index: 1999;`
- `height: 56px;`
- `width: 100%;`
- `margin-top: 0;` (ZERO gap from A0)

### Main Content Wrapper
- `height: calc(100vh - 120px);` (100vh - A0 - A1)
- `display: flex; flex-direction: column;`
- `overflow: hidden;`

### 3-Column Grid Layout
- `display: grid;`
- `grid-template-columns: 260px 1fr 260px;`
- `gap: 0;`
- `height: 100%;`

### Left Sidebar (A6-A11)
- `position: sticky; top: 120px;`
- `height: calc(100vh - 120px);`
- `overflow: hidden;` (NO SCROLL)
- `display: flex; flex-direction: column; gap: 12px;`

### Right Sidebar (A12-A17)
- `position: sticky; top: 120px;`
- `height: calc(100vh - 120px);`
- `overflow: hidden;` (NO SCROLL)
- `display: flex; flex-direction: column; gap: 12px;`

### Center Column (A2-A5)
- `height: 100%;`
- `overflow-y: auto;` (ONLY center scrolls)
- `overflow-x: hidden;`

## Slot Mapping

| Slot ID | Location | Description |
|---------|----------|-------------|
| A0 | Header | Navbar (sticky top) |
| A1 | Header | Moving strip (sticky below A0) |
| A2 | Center | Presentation banner + logo |
| A3 | Center | "Animalele lunii" grid (2x3) |
| A4 | Center | "New Entries" grid (7 columns) |
| A5 | Center | Partners banner |
| A6 | Left Sidebar | Advertisement slot 1 |
| A7 | Left Sidebar | Advertisement slot 2 |
| A8 | Left Sidebar | Advertisement slot 3 |
| A9 | Left Sidebar | Advertisement slot 4 |
| A10 | Left Sidebar | Advertisement slot 5 |
| A11 | Left Sidebar | Advertisement slot 6 |
| A12 | Right Sidebar | Advertisement slot 1 |
| A13 | Right Sidebar | Advertisement slot 2 |
| A14 | Right Sidebar | Advertisement slot 3 |
| A15 | Right Sidebar | Advertisement slot 4 |
| A16 | Right Sidebar | Advertisement slot 5 |
| A17 | Right Sidebar | Advertisement slot 6 |

## Files

- **CSS**: `static/css/home-skeleton.css` - Main skeleton CSS
- **Template**: `templates/base.html` - Base structure (A0, A1 block, layout wrapper)
- **Home Template**: `templates/anunturi/home.html` - A1 content, A2-A5 content
- **Left Sidebar**: `templates/components/sidebar_left.html` - A6-A11
- **Right Sidebar**: `templates/components/sidebar_right.html` - A12-A17

## Verification Checklist

- [x] A0 height is compact (64px)
- [x] A1 sits immediately below A0 (top: 64px, margin-top: 0)
- [x] Zero gap between A0 and A1
- [x] Sidebars are frozen (overflow: hidden, NO scroll)
- [x] Only center column scrolls (overflow-y: auto)
- [x] All IDs A0-A17 are present and unique
- [x] No vertical gaps between A0-A1-A2
- [x] 3-column layout below A0+A1
