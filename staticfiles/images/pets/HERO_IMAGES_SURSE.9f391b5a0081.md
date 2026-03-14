# 10 poze pentru hero (caseta cu sigle) – animale, păduri, păsări, colorat

**Dimensiuni recomandate:** landscape 1200×400 px sau 1600×500 px (raport ~2:1 sau 3:1).

După ce descarci pozele, pune-le în acest folder (`static/images/pets/`) și adaugă căile în `home/data.py` în lista `HERO_SLIDER_IMAGES`.

---

## Surse gratuite (royalty-free)

### Unsplash (unsplash.com)
- Câini / animale: https://unsplash.com/s/photos/dog-landscape
- Pădure colorată: https://unsplash.com/s/photos/colorful-forest
- Păsări / natură: https://unsplash.com/s/photos/birds-nature
- Animale în natură: https://unsplash.com/s/photos/wildlife-landscape

### Pexels (pexels.com)
- Câini în natură: https://www.pexels.com/search/dogs%20nature/
- Pădure: https://www.pexels.com/search/forest/
- Păsări: https://www.pexels.com/search/birds/
- Peisaje colorate: https://www.pexels.com/search/colorful%20landscape/

### Pixabay (pixabay.com)
- Câini: https://pixabay.com/images/search/dog/
- Animale natură: https://pixabay.com/images/search/wildlife/
- Pădure: https://pixabay.com/images/search/forest/

### Alte surse
- **PxHere** (pxhere.com): wildlife, forest, CC0
- **Free Nature Stock** (freenaturestock.com): peisaje, toamnă, păduri
- **Picjumbo** (picjumbo.com): natură, păduri

---

## Cum folosești pozele

1. Descarci 10 poze landscape (animale / păduri / păsări / colorat).
2. Le redimensionezi la ~1200×400 px sau 1600×500 px (opțional, dar recomandat).
3. Le salvezi în `euadopt_final/static/images/pets/`, ex.: `hero_01.jpg`, `hero_02.jpg`, …
4. În `home/data.py` actualizezi:

```python
HERO_SLIDER_IMAGES = [
    "images/pets/hero_01.jpg",
    "images/pets/hero_02.jpg",
    # ... până la hero_10.jpg
]
```

Pozele se vor roti în caseta cu sigle de pe homepage.
