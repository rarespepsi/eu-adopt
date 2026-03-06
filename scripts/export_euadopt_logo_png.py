"""
Export EU-Adopt logo (dog + stars) from SVG to PNG with transparent background.
Uses Playwright to render SVG (no Cairo dependency on Windows).
Output: static/images/euadopt-logo.png (320x320)
"""
import os
import sys
import base64

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
os.chdir(ROOT)

SVG_PATH = os.path.join(ROOT, "static", "images", "sigla-logo-final.svg")
OUT_PATH = os.path.join(ROOT, "static", "images", "logo-final-cu-stele.png")

def main():
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("Installing playwright...")
        import subprocess
        subprocess.check_call([sys.executable, "-m", "pip", "install", "playwright", "-q"])
        subprocess.check_call([sys.executable, "-m", "playwright", "install", "chromium"])
        from playwright.sync_api import sync_playwright

    if not os.path.isfile(SVG_PATH):
        print("Error: SVG not found at", SVG_PATH)
        sys.exit(1)

    with open(SVG_PATH, "rb") as f:
        svg_data = f.read().decode("utf-8", errors="replace")

    # Escape for HTML
    svg_b64 = base64.b64encode(svg_data.encode("utf-8")).decode("ascii")
    html = f"""<!DOCTYPE html><html><head><style>
      body {{ margin:0; background:transparent; }}
      img {{ display:block; width:320px; height:320px; }}
    </style></head><body>
    <img src="data:image/svg+xml;base64,{svg_b64}" width="320" height="320" alt="" />
    </body></html>"""

    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={"width": 320, "height": 320})
        page.set_content(html, wait_until="load")
        page.locator("img").first.screenshot(path=OUT_PATH)
        browser.close()

    print("Saved:", OUT_PATH)

if __name__ == "__main__":
    main()
