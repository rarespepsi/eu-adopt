from django.shortcuts import render

def home(request):
    return render(request, "anunturi/home.html")
def pets_all(request):
    return render(request, "anunturi/pets-all.html")


