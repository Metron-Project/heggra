from django.urls import include, path

urlpatterns = [
    path("heggra/", include("heggra.urls")),
]
