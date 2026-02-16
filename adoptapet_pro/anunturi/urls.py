from django.urls import path
from django.views.generic import RedirectView
from .views import home, pets_all, pets_single, adoption_request_submit

urlpatterns = [
    path("", home, name="home"),
    path("index.html", home, name="home_index"),
    path("pets-all.html", pets_all, name="pets_all"),
    path("pet/<int:pk>/", pets_single, name="pets_single"),
    path("adoption/request/<int:pk>/", adoption_request_submit, name="adoption_request_submit"),
    path("pets-single.html", RedirectView.as_view(pattern_name="pets_all", permanent=False), name="pets_single_redirect"),
]


