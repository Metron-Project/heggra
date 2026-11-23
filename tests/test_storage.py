import gc
from datetime import timedelta

import pytest
from django.core.files.storage import InMemoryStorage
from django.core.files.uploadedfile import SimpleUploadedFile
from django.utils import timezone

from heggra import storage

RULES = {"name": "attachment", "max_size": None, "accept": [], "image": False}


class ObjectStorage(InMemoryStorage):
    """A storage where heggra's folder doesn't exist, like a prefix on S3."""

    def exists(self, name):
        return name != storage.TEMP_DIR and super().exists(name)


def upload(name="notes.txt", content=b"hello"):
    return SimpleUploadedFile(name, content, content_type="text/plain")


def test_round_trip():
    token = storage.save_temporary(upload(), RULES)
    file = storage.open_token(token, RULES)
    assert file is not None
    assert file.name == "notes.txt"
    assert file.size == 5
    assert file.content_type == "text/plain"
    assert file.read() == b"hello"
    assert file.token == token


def test_upload_is_opened_when_read():
    token = storage.save_temporary(upload(), RULES)
    file = storage.open_token(token, RULES)
    assert file.closed
    assert file.read() == b"hello"
    assert not file.closed
    file.close()
    assert file.closed
    assert file.open().read() == b"hello"
    file.close()


def test_upload_closes_when_it_is_no_longer_used():
    file = storage.open_token(storage.save_temporary(upload(), RULES), RULES)
    file.read()
    content = file.file
    del file
    gc.collect()
    assert content.closed


def test_open_rewinds_an_open_upload():
    file = storage.open_token(storage.save_temporary(upload(), RULES), RULES)
    file.read()
    assert file.open().read() == b"hello"
    file.close()


def test_closing_an_unread_upload():
    file = storage.open_token(storage.save_temporary(upload(), RULES), RULES)
    file.close()
    assert file.closed


def test_file_is_saved_under_the_temporary_folder(media_root):
    storage.save_temporary(upload(), RULES)
    assert len(list((media_root / storage.TEMP_DIR).glob("*/notes.txt"))) == 1


def test_unsafe_names_are_cleaned():
    token = storage.save_temporary(upload("../../etc/pass wd"), RULES)
    assert storage.open_token(token, RULES).name == "pass_wd"


@pytest.mark.parametrize("name", ["", "...", " . ", "@@@", "$$$", "../.."])
def test_empty_names_get_a_default(name):
    assert storage.clean_name(name) == "upload"


def test_upload_without_a_usable_name():
    token = storage.save_temporary(upload("@@@"), RULES)
    assert storage.open_token(token, RULES).name == "upload"


def test_token_is_bound_to_its_rules():
    token = storage.save_temporary(upload(), RULES)
    assert storage.open_token(token, {**RULES, "name": "other"}) is None


def test_tampered_token():
    token = storage.save_temporary(upload(), RULES)
    assert storage.open_token(token + "x", RULES) is None


def test_expired_token(settings):
    token = storage.save_temporary(upload(), RULES)
    settings.HEGGRA_MAX_AGE = -1
    assert storage.open_token(token, RULES) is None


def test_missing_file():
    token = storage.save_temporary(upload(), RULES)
    storage.get_storage().delete(storage.load_token(token)["path"])
    assert storage.open_token(token, RULES) is None


def test_content_type_is_guessed_when_missing():
    file = upload("notes.txt")
    file.content_type = None
    token = storage.save_temporary(file, RULES)
    assert storage.open_token(token, RULES).content_type == "text/plain"


def test_upload_context_without_preview():
    context = storage.upload_context("notes.txt", 5, "token", RULES)
    assert context == {
        "field_name": "attachment",
        "name": "notes.txt",
        "preview_url": None,
        "size": 5,
        "token": "token",
    }


def test_cleanup_deletes_only_old_uploads(media_root):
    storage.save_temporary(upload(), RULES)
    assert storage.cleanup() == 0
    assert storage.cleanup(timezone.now() + timedelta(days=2)) == 1
    assert list((media_root / storage.TEMP_DIR).iterdir()) == []


def test_cleanup_without_uploads():
    assert storage.cleanup() == 0


def test_cleanup_with_storage_without_folders(settings):
    settings.STORAGES = {
        **settings.STORAGES,
        "heggra": {"BACKEND": "django.core.files.storage.InMemoryStorage"},
    }
    settings.HEGGRA_STORAGE = "heggra"
    storage.save_temporary(upload(), RULES)
    assert storage.cleanup(timezone.now() + timedelta(days=2)) == 1


def test_cleanup_with_storage_whose_folders_dont_exist(settings):
    settings.STORAGES = {
        **settings.STORAGES,
        "heggra": {"BACKEND": "tests.test_storage.ObjectStorage"},
    }
    settings.HEGGRA_STORAGE = "heggra"
    storage.save_temporary(upload(), RULES)
    assert not storage.get_storage().exists(storage.TEMP_DIR)
    assert storage.cleanup(timezone.now() + timedelta(days=2)) == 1
