"""System checks for heggra's settings."""

from collections.abc import Sequence
from typing import Any

from django.apps import AppConfig
from django.conf import settings
from django.core.checks import Error
from django.core.checks import Warning as CheckWarning

from .storage import get_login_required

AUTHENTICATION_MIDDLEWARE = "django.contrib.auth.middleware.AuthenticationMiddleware"


def check_storage(app_configs: Sequence[AppConfig] | None, **kwargs: Any) -> list[Error]:
    """Return an error if ``HEGGRA_STORAGE`` doesn't name a storage in ``STORAGES``."""
    alias = getattr(settings, "HEGGRA_STORAGE", "default")
    if alias in settings.STORAGES:
        return []
    return [
        Error(
            f"HEGGRA_STORAGE is {alias!r}, which isn't in STORAGES.",
            hint="Add it to STORAGES, or set HEGGRA_STORAGE to an alias that is.",
            id="heggra.E001",
        )
    ]


def check_login_required(
    app_configs: Sequence[AppConfig] | None, **kwargs: Any
) -> list[CheckWarning]:
    """Return a warning if ``HEGGRA_LOGIN_REQUIRED`` can't read ``request.user``."""
    if not get_login_required():
        return []
    if AUTHENTICATION_MIDDLEWARE in settings.MIDDLEWARE:
        return []
    return [
        CheckWarning(
            "HEGGRA_LOGIN_REQUIRED, which is True by default, needs request.user, so uploads "
            "fail without AuthenticationMiddleware.",
            hint=f"Add {AUTHENTICATION_MIDDLEWARE!r} to MIDDLEWARE, set HEGGRA_LOGIN_REQUIRED = "
            "False to let anyone upload, or silence this check if another middleware sets "
            "request.user.",
            id="heggra.W001",
        )
    ]
