"""Settings for the heggra example project, which is for local development only."""

from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = "heggra-example-only"  # noqa: S105
DEBUG = True
ALLOWED_HOSTS = ["localhost", "127.0.0.1"]

INSTALLED_APPS = [
    "django.contrib.contenttypes",
    "django.contrib.staticfiles",
    "heggra",
    "comics",
]
MIDDLEWARE = [
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
]
ROOT_URLCONF = "project.urls"
TEMPLATES = [{"BACKEND": "django.template.backends.django.DjangoTemplates", "APP_DIRS": True}]
DATABASES = {"default": {"ENGINE": "django.db.backends.sqlite3", "NAME": BASE_DIR / "db.sqlite3"}}
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
STATIC_URL = "static/"

# Saved covers and scripts, served by runserver at MEDIA_URL.
MEDIA_ROOT = BASE_DIR / "media"
MEDIA_URL = "media/"

STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"},
    # Uploads wait here until their form is saved. It has no URL, so nothing in it is served
    # before then; image previews go through heggra's preview view instead.
    "uploads": {
        "BACKEND": "django.core.files.storage.FileSystemStorage",
        "OPTIONS": {"location": BASE_DIR / "uploads"},
    },
}
HEGGRA_STORAGE = "uploads"
# The example has no accounts, so anyone can upload. A real site with logins leaves this out.
HEGGRA_LOGIN_REQUIRED = False

# Bulma classes for heggra's elements, which otherwise carry only their heggra-* classes. Bulma's
# file element has the same structure as the widget, with the file input inside its label, and
# hides the input itself. comics/static/comics/site.css adds the little Bulma has no class for.
HEGGRA_CLASSES = {
    "dropzone": "file is-boxed",
    "dropzone_active": "is-primary",
    "label": "file-label",
    "input": "file-input",
    "button": "file-cta",
    "hint": "help has-text-centered",
    "progress": "progress is-small is-primary",
    "error": "help is-danger",
    "current": "box",
    "file": "box",
    "file_name": "has-text-weight-semibold",
    "file_size": "has-text-grey",
    "remove": "button is-small",
    "clear": "checkbox",
}
