from django.urls import path
from . import views

urlpatterns = [
    path('', views.home_view, name='home'),
    path('servicii/', views.servicii_view, name='servicii'),

    path('pets/', views.home_view, name='pets_all'),
    path('pets/<int:pk>/', views.dog_profile_view, name='pets_single'),
]