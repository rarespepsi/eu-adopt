from django.urls import path
from . import views

urlpatterns = [
    path('', views.home_view, name='home'),
    path('servicii/', views.servicii_view, name='servicii'),
    path('transport/', views.transport_view, name='transport'),

    path('custi/', views.custi_view, name='custi'),
    path('shop/', views.shop_view, name='shop'),

    path('pets/', views.home_view, name='pets_all'),
    path('pets/<int:pk>/', views.dog_profile_view, name='pets_single'),
]