"""Temporary storage for files uploaded ahead of the form they belong to."""

import contextlib
import mimetypes
import uuid
import weakref
from datetime import datetime, timedelta
from pathlib import Path, PurePosixPath
from typing import Any, Self, TypedDict, override

from django.conf import settings
from django.core import signing
from django.core.exceptions import SuspiciousFileOperation
from django.core.files.storage import FileSystemStorage, Storage, storages
from django.core.files.uploadedfile import UploadedFile
from django.urls import reverse
from django.utils import timezone
from django.utils.text import get_valid_filename

TEMP_DIR = "heggra"
TOKEN_SALT = "heggra.upload"  # noqa: S105 - a signing namespace, not a secret.
CONFIG_SALT = "heggra.config"
DEFAULT_MAX_AGE = 60 * 60 * 24


class Rules(TypedDict):
    """What a widget accepts, which an upload's token is bound to."""

    name: str
    max_size: int | None
    accept: list[str]
    image: bool


class TemporaryUpload(UploadedFile):
    """A file waiting in temporary storage, with the token that refers to it.

    The stored file is opened when it's first read, since a form reads an upload's value more
    often than its content.
    """

    def __init__(self, token: str, path: str, **kwargs: Any) -> None:
        self.path = path
        self._file: Any = None
        super().__init__(**kwargs)
        self.token = token

    @property
    def file(self) -> Any:
        """Return the stored file, opening it if it isn't open."""
        if self._file is None:
            self._file = get_storage().open(self.path, "rb")
            # Nothing closes a file once a form has read or saved it, so it closes with the upload.
            weakref.finalize(self, self._file.close)
        return self._file

    @file.setter
    def file(self, value: Any) -> None:  # pyright: ignore[reportIncompatibleVariableOverride]
        self._file = value

    @property
    @override
    def closed(self) -> bool:
        return self._file is None or self._file.closed

    @override
    def open(self, mode: str | None = None) -> Self:  # pyright: ignore[reportIncompatibleMethodOverride]
        if self.closed:
            self._file = None
        else:
            self.seek(0)
        return self

    @override
    def close(self) -> None:
        if self._file is not None:
            self._file.close()


def get_storage() -> Storage:
    """Return the storage that holds uploads until their form is saved."""
    return storages[getattr(settings, "HEGGRA_STORAGE", "default")]


def get_max_age() -> int:
    """Return how many seconds an upload stays usable."""
    return getattr(settings, "HEGGRA_MAX_AGE", DEFAULT_MAX_AGE)


def clean_name(name: str) -> str:
    """Return ``name`` made safe to store, or ``"upload"`` if nothing of it is."""
    name = PurePosixPath(name).name
    try:
        name = get_valid_filename(name)
    except SuspiciousFileOperation:
        return "upload"
    return name if name.strip(".") else "upload"


def save_temporary(file: UploadedFile, rules: Rules) -> str:
    """Save ``file`` to temporary storage and return a signed token for it."""
    name = clean_name(file.name or "")
    path = get_storage().save(f"{TEMP_DIR}/{uuid.uuid4().hex}/{name}", file)
    payload = {"path": path, "name": name, "type": file.content_type, "rules": rules}
    return signing.dumps(payload, salt=TOKEN_SALT, compress=True)


def load_token(token: str) -> dict[str, Any] | None:
    """Return a token's payload, or ``None`` if it is invalid or expired."""
    try:
        return signing.loads(token, salt=TOKEN_SALT, max_age=get_max_age())
    except signing.BadSignature:
        return None


def open_token(token: str, rules: Rules) -> TemporaryUpload | None:
    """Open the upload behind ``token``, if the token is valid and was issued for ``rules``."""
    payload = load_token(token)
    if payload is None or payload["rules"] != rules:
        return None
    try:
        size = get_storage().size(payload["path"])
    except FileNotFoundError:
        return None
    content_type = payload["type"] or mimetypes.guess_type(payload["name"])[0]
    return TemporaryUpload(
        token, payload["path"], name=payload["name"], content_type=content_type, size=size
    )


def upload_context(name: str, size: int, token: str, rules: Rules) -> dict[str, Any]:
    """Return the template context describing an upload."""
    return {
        "field_name": rules["name"],
        "name": name,
        "preview_url": reverse("heggra:preview", args=[token]) if rules["image"] else None,
        "size": size,
        "token": token,
    }


def cleanup(now: datetime | None = None) -> int:
    """Delete uploads older than ``HEGGRA_MAX_AGE`` and return how many were deleted."""
    storage = get_storage()
    cutoff = (now or timezone.now()) - timedelta(seconds=get_max_age())
    deleted = 0
    # Object storages such as S3 have no folders, so exists() is false for the prefix.
    try:
        folders, _ = storage.listdir(TEMP_DIR)
    except FileNotFoundError:
        return 0
    for folder in folders:
        folder_path = f"{TEMP_DIR}/{folder}"
        _, files = storage.listdir(folder_path)
        for filename in files:
            path = f"{folder_path}/{filename}"
            if storage.get_modified_time(path) < cutoff:
                storage.delete(path)
                deleted += 1
        _remove_empty_folder(storage, folder_path)
    return deleted


def _remove_empty_folder(storage: Storage, path: str) -> None:
    # Only the filesystem leaves empty folders behind. A folder still holding newer files stays.
    if isinstance(storage, FileSystemStorage):
        with contextlib.suppress(OSError):
            Path(storage.path(path)).rmdir()
