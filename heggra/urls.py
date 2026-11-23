"""URL patterns for the upload and preview endpoints."""

from django.urls import path

from . import views

app_name = "heggra"

urlpatterns = [
    path("upload/", views.upload, name="upload"),
    path("preview/<str:token>/", views.preview, name="preview"),
]
