from io import StringIO

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.management import call_command

from heggra import storage

RULES = {"name": "attachment", "max_size": None, "accept": [], "image": False}


def run():
    out = StringIO()
    call_command("heggra_cleanup", stdout=out)
    return out.getvalue().strip()


@pytest.mark.parametrize(
    ("count", "message"), [(1, "Deleted 1 expired upload."), (2, "Deleted 2 expired uploads.")]
)
def test_cleanup(settings, count, message):
    for _ in range(count):
        storage.save_temporary(SimpleUploadedFile("a.txt", b"a"), RULES)
    settings.HEGGRA_MAX_AGE = -1
    assert run() == message


def test_cleanup_keeps_fresh_uploads():
    storage.save_temporary(SimpleUploadedFile("a.txt", b"a"), RULES)
    assert run() == "Deleted 0 expired uploads."
