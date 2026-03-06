# -*- coding: utf-8 -*-
"""Generează sigla EU Adopt într-o singură imagine: formă rotundă, câine+pisică + stele (identică cu A0)."""
import base64
import os

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(SCRIPT_DIR)  # adoptapet_pro
JPEG_PATH = os.path.join(PROJECT_ROOT, "static", "images", "eu-adopt-logo-original.jpeg")

with open(JPEG_PATH, "rb") as f:
    img_b64 = base64.standard_b64encode(f.read()).decode("ascii")

# Stele 12 (galben #FFD700, albastru #003399) - din style.css .the_logo_link::before, viewBox 300x300
STARS_SVG = '''<g transform="translate(160,160) scale(0.8667) translate(-150,-150)">
<path d="M254.0,160.0L251.6,153.2L244.5,153.1L250.2,148.8L248.1,141.9L254.0,146.0L259.9,141.9L257.8,148.8L263.5,153.1L256.4,153.2Z" fill="#FFD700"/>
<path d="M235.1,210.7L236.4,203.6L230.3,199.9L237.4,199.0L239.0,192.1L242.1,198.5L249.2,197.9L244.0,202.8L246.8,209.4L240.5,206.0Z" fill="#003399"/>
<path d="M193.3,245.1L198.0,239.6L204.6,243.4L201.2,236.2L206.1,230.9L205.5,238.1L211.9,241.1L205.0,242.7L204.1,249.8L200.4,243.7Z" fill="#FFD700"/>
<path d="M140.0,254.0L146.8,251.6L146.9,244.5L151.2,250.2L158.1,248.1L154.0,254.0L158.1,259.9L151.2,257.8L146.9,263.5L146.8,256.4Z" fill="#003399"/>
<path d="M89.3,235.1L96.4,236.4L100.1,230.3L101.0,237.4L107.9,239.0L101.5,242.1L102.1,249.2L97.2,244.0L90.6,246.8L94.0,240.5Z" fill="#FFD700"/>
<path d="M54.9,193.3L60.4,198.0L66.6,194.6L63.8,201.2L69.1,206.1L61.9,205.5L58.9,211.9L57.3,205.0L50.2,204.1L56.3,200.4Z" fill="#003399"/>
<path d="M46.0,140.0L48.4,146.8L55.5,146.9L49.8,151.2L51.9,158.1L46.0,154.0L40.1,158.1L42.2,151.2L36.5,146.9L43.6,146.8Z" fill="#FFD700"/>
<path d="M64.9,89.3L63.6,96.4L69.7,100.1L62.6,101.0L61.0,107.9L57.9,101.5L50.8,102.1L56.0,97.2L53.2,90.6L59.5,94.0Z" fill="#003399"/>
<path d="M106.7,54.9L102.0,60.4L105.4,66.6L98.8,63.8L93.9,69.1L94.5,61.9L88.1,58.9L95.0,57.3L95.9,50.2L99.6,56.3Z" fill="#FFD700"/>
<path d="M160.0,46.0L153.2,48.4L153.1,55.5L148.8,49.8L141.9,51.9L146.0,46.0L141.9,40.1L148.8,42.2L153.1,36.5L153.2,43.6Z" fill="#003399"/>
<path d="M210.7,64.9L203.6,63.6L199.9,69.7L199.0,62.6L192.1,61.0L198.5,57.9L197.9,60.8L202.8,56.0L209.4,63.2L206.0,69.5Z" fill="#FFD700"/>
<path d="M255.1,116.7L249.6,112.0L243.4,115.4L246.2,108.8L240.9,103.9L248.1,104.5L251.1,98.1L252.7,105.0L259.8,105.9L253.7,109.6Z" fill="#003399"/>
</g>'''

# SVG 320x320: cerc alb r=114.5, imagine 229x229 centrată, stele (260px echiv) pe margine
svg = f'''<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" viewBox="0 0 320 320" width="320" height="320">
  <defs>
    <clipPath id="circle-clip">
      <circle cx="160" cy="160" r="130"/>
    </clipPath>
  </defs>
  <!-- Cerc alb fundal (ca în A0) -->
  <circle cx="160" cy="160" r="130" fill="#FFFFFF"/>
  <!-- Stele galbene și albastre pe margini (260px diametru) -->
  {STARS_SVG}
  <!-- Câine + pisică centru 229x229 -->
  <image xlink:href="data:image/jpeg;base64,{img_b64}" x="45.5" y="45.5" width="229" height="229" preserveAspectRatio="xMidYMid meet"/>
</svg>
'''

out_svg = os.path.join(SCRIPT_DIR, "sigla-logo-final.svg")
with open(out_svg, "w", encoding="utf-8") as f:
    f.write(svg)
print("Scris:", out_svg)
