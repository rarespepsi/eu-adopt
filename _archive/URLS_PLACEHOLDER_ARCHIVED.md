# Rute URL scoase din proiectul activ (martie 2026)

**Scop:** Material de informare pentru viitor. Aceste rute nu mai sunt în `home/urls.py`; toate duceau la același `home_view` → `home_v2.html` (HOME). În proiectul nou rămân active doar: `''` (home), `pets/`, `pets/<int:pk>/`.

## Rute arhivate (copie pentru referință)

```python
path('servicii/', views.home_view, name='servicii'),
path('transport/', views.home_view, name='transport'),
path('shop/', views.home_view, name='shop'),

path('login/', views.home_view, name='login'),
path('logout/', views.home_view, name='logout'),
path('register/', views.home_view, name='register'),

path('contact/', views.home_view, name='contact'),
path('termeni/', views.home_view, name='termeni'),
path('search/', views.home_view, name='site_search'),

path('analiza/', views.home_view, name='analiza'),
path('wishlist/', views.home_view, name='wishlist'),
path('my-wishlist/', views.home_view, name='my_wishlist'),
path('cont/', views.home_view, name='cont'),
path('profil/', views.home_view, name='cont_profil'),
```

Pentru pagini viitoare (Servicii, Transport, Contact etc.) se pot adăuga din nou rute și template-uri proprii.
