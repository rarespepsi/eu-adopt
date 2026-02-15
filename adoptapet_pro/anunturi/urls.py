from django.urls import path
from .views import home, pets_all

urlpatterns = [
    path("", home, name="home"),
    path("index.html", home, name="home_index"),
    path("pets-all.html", pets_all, name="pets_all"),
]


