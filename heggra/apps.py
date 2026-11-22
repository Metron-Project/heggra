"""Django app configuration."""

from typing import override

from django.apps import AppConfig
from django.core import checks

from .checks import check_login_required, check_storage


class HeggraConfig(AppConfig):
    """Register heggra's system checks."""

    name = "heggra"

    @override
    def ready(self) -> None:
        checks.register(check_storage)
        checks.register(check_login_required)
