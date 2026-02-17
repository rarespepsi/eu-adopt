from django.urls import path
from django.contrib.auth import views as auth_views
from django.views.generic import RedirectView
from .views import (
    home, pets_all, pets_single, adoption_request_submit,
    signup_view, signup_verificare_telefon_view,
    contact_view, termeni_view, schema_site_view,
    cont_view, cont_profil_view, cont_ong_view, cont_adauga_animal_view, cont_ong_adauga_view,
)

urlpatterns = [
    path("", home, name="home"),
    path("index.html", home, name="home_index"),
    path("pets-all.html", pets_all, name="pets_all"),
    path("pet/<int:pk>/", pets_single, name="pets_single"),
    path("adoption/request/<int:pk>/", adoption_request_submit, name="adoption_request_submit"),
    path("pets-single.html", RedirectView.as_view(pattern_name="pets_all", permanent=False), name="pets_single_redirect"),
    # Auth
    path("cont/", cont_view, name="cont"),
    path("cont/login/", auth_views.LoginView.as_view(template_name="registration/login.html"), name="login"),
    path("cont/logout/", auth_views.LogoutView.as_view(), name="logout"),
    path("cont/inregistrare/", signup_view, name="signup"),
    path("cont/verificare-telefon/", signup_verificare_telefon_view, name="signup_verificare_telefon"),
    # Pagini statice
    path("contact/", contact_view, name="contact"),
    path("termeni/", termeni_view, name="termeni"),
    path("schema-site/", schema_site_view, name="schema_site"),
    path("cont/profil/", cont_profil_view, name="cont_profil"),
    path("cont/ong/", cont_ong_view, name="cont_ong"),
    path("cont/adauga-animal/", cont_adauga_animal_view, name="cont_adauga_animal"),
    path("cont/ong/adauga/", cont_ong_adauga_view, name="cont_ong_adauga"),
]


