from django.http import HttpResponse
from django.shortcuts import render
from django.urls import include, path

from .forms import DocumentForm


def document_form(request):
    auto_id = request.GET.get("auto_id", "id_%s")
    form = DocumentForm(request.POST or None, request.FILES or None, auto_id=auto_id)
    if form.is_valid():
        document = form.save()
        return HttpResponse(f"saved {document.attachment.name} {document.cover.name}")
    return render(request, "form.html", {"form": form})


def login(request):
    return HttpResponse("<form><input name='username'></form>")


urlpatterns = [
    path("login/", login),
    path("heggra/", include("heggra.urls")),
    path("form/", document_form),
]
