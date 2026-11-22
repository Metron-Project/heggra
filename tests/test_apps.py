from django.apps import apps

from heggra.apps import HeggraConfig


def test_app_is_installed():
    assert isinstance(apps.get_app_config("heggra"), HeggraConfig)
