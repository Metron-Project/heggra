from django.http import HttpResponse
from django.shortcuts import render
from django.urls import include, path

from .forms import DocumentForm


def document_form(request):
    form = DocumentForm(request.POST or None, request.FILES or None)
    if form.is_valid():
        document = form.save()
        return HttpResponse(f"saved {document.attachment.name} {document.cover.name}")
    return render(request, "form.html", {"form": form})


urlpatterns = [
    path("heggra/", include("heggra.urls")),
    path("form/", document_form),
]
