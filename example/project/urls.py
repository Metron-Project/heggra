"""URL patterns for the example project."""

from django.conf import settings
from django.conf.urls.static import static
from django.urls import include, path

urlpatterns = [
    # The upload and preview endpoints that every UploadWidget calls.
    path("heggra/", include("heggra.urls")),
    path("", include("comics.urls")),
    # Serves saved files while DEBUG is on. Use your web server or storage in production.
    *static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT),
]
