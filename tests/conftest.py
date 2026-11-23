import pytest


@pytest.fixture(autouse=True)
def media_root(settings, tmp_path):
    settings.MEDIA_ROOT = tmp_path / "media"
    return settings.MEDIA_ROOT


@pytest.fixture
def lazy_storage(request, settings):
    """Keep uploads in a storage that opens files lazily, like S3's, when the param is true."""
    if getattr(request, "param", True):
        settings.STORAGES = {
            **settings.STORAGES,
            "heggra": {"BACKEND": "tests.storages.LazyStorage"},
        }
        settings.HEGGRA_STORAGE = "heggra"
