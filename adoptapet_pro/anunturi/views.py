from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages

from .models import Pet, AdoptionRequest
from .forms import AdoptionRequestForm
from .adoption_platform import platform_validation_passes, send_adoption_request_to_ong


def home(request):
    return render(request, "anunturi/home.html")


def pets_all(request):
    return render(request, "anunturi/pets-all.html")


def pets_single(request, pk):
    pet = get_object_or_404(Pet, pk=pk)
    form = AdoptionRequestForm()
    return render(request, "anunturi/pets-single.html", {
        "pet": pet,
        "adoption_form": form,
    })


def adoption_request_submit(request, pk):
    pet = get_object_or_404(Pet, pk=pk)
    if request.method != "POST":
        return redirect("pets_single", pk=pk)
    form = AdoptionRequestForm(request.POST)
    if not form.is_valid():
        return render(request, "anunturi/pets-single.html", {
            "pet": pet,
            "adoption_form": form,
        })
    adoption_request = form.save(commit=False)
    adoption_request.pet = pet
    adoption_request.status = "new"
    adoption_request.save()

    if platform_validation_passes(adoption_request):
        adoption_request.status = "approved_platform"
        adoption_request.save()
        send_adoption_request_to_ong(adoption_request, request)
        messages.success(request, "Cererea a fost trimisă. Vă vom contacta în curând.")
    else:
        messages.info(request, "Cererea a fost înregistrată. Echipa noastră o va verifica și vă vom contacta.")

    return redirect("pets_single", pk=pk)


