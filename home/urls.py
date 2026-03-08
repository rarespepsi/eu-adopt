from django.urls import path
from . import views

urlpatterns = [
    path('', views.home_view, name='home'),

    path('pets/', views.home_view, name='pets_all'),
    path('pets/<int:pk>/', views.dog_profile_view, name='pets_single'),
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
]