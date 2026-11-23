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
# How long cleanup waits after a token expires, so it can't delete a file a form is still saving.
CLEANUP_GRACE = 60 * 60
# Filesystems limit a file name's bytes, usually to 255, while UploadedFile limits its characters.
MAX_NAME_BYTES = 200
# A form FileField refuses longer names, and a model FileField gives it a max_length of 100.
MAX_NAME_LENGTH = 100
# The image types browsers can show, the only ones the widget previews. Pillow opens many more,
# such as TIFF and PSD, which would show as a broken image.
PREVIEW_TYPES = frozenset(
    {
        "image/avif",
        "image/bmp",
        "image/gif",
        "image/jpeg",
        "image/png",
        "image/webp",
        "image/x-icon",
    }
)
PREVIEW_EXTENSIONS = frozenset({".avif", ".bmp", ".gif", ".ico", ".jpeg", ".jpg", ".png", ".webp"})


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
        # The next read opens the stored file again, as Django reads an image's dimensions and
        # closes it before saving it.
        if self._file is not None:
            self._file.close()
            self._file = None


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
    if not name.strip("."):
        return "upload"
    if len(name) > MAX_NAME_LENGTH or len(name.encode()) > MAX_NAME_BYTES:
        suffix = PurePosixPath(name).suffix
        # The extension is kept, unless it's so long that it isn't one.
        if len(suffix) > MAX_NAME_LENGTH // 2 or len(suffix.encode()) > MAX_NAME_BYTES // 2:
            suffix = ""
        stem = name.removesuffix(suffix)[: MAX_NAME_LENGTH - len(suffix)]
        stem = stem.encode()[: MAX_NAME_BYTES - len(suffix.encode())].decode(errors="ignore")
        name = stem + suffix
    return name


def save_temporary(file: UploadedFile, rules: Rules) -> TemporaryUpload:
    """Save ``file`` to temporary storage and return it, with a signed token for it."""
    name = clean_name(file.name or "")
    path = get_storage().save(f"{TEMP_DIR}/{uuid.uuid4().hex}/{name}", file)
    payload = {"path": path, "name": name, "type": file.content_type, "rules": rules}
    token = signing.dumps(payload, salt=TOKEN_SALT, compress=True)
    return TemporaryUpload(token, path, name=name, content_type=file.content_type, size=file.size)


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
    storage = get_storage()
    # Storages differ in what they raise for a missing file, but exists() works on all of them.
    if not storage.exists(payload["path"]):
        return None
    try:
        size = storage.size(payload["path"])
    except FileNotFoundError:
        return None
    content_type = payload["type"]
    # An image's type is the one Pillow detected, if any, which decides whether it has a preview.
    if content_type is None and not payload["rules"]["image"]:
        content_type = mimetypes.guess_type(payload["name"])[0]
    return TemporaryUpload(
        token, payload["path"], name=payload["name"], content_type=content_type, size=size
    )


def has_preview(rules: Rules, content_type: str | None) -> bool:
    """Return whether an upload checked against ``rules`` is an image browsers can show."""
    return rules["image"] and content_type in PREVIEW_TYPES


def upload_context(
    name: str, size: int, token: str, rules: Rules, content_type: str | None
) -> dict[str, Any]:
    """Return the template context describing an upload."""
    preview = has_preview(rules, content_type)
    return {
        "field_name": rules["name"],
        "name": name,
        "preview_url": reverse("heggra:preview", args=[token]) if preview else None,
        "size": size,
        "token": token,
    }


def cleanup(now: datetime | None = None) -> int:
    """Delete uploads older than ``HEGGRA_MAX_AGE`` plus an hour, and return how many were deleted.

    A file is saved just before its token is signed, so it's a little older than the token, and a
    form that checked a token about to expire reads the file only when it saves.
    """
    storage = get_storage()
    cutoff = (now or timezone.now()) - timedelta(seconds=get_max_age() + CLEANUP_GRACE)
    deleted = 0
    # Object storages such as S3 have no folders, so exists() is false for the prefix.
    try:
        folders, _ = storage.listdir(TEMP_DIR)
    except FileNotFoundError:
        return 0
    for folder in folders:
        folder_path = f"{TEMP_DIR}/{folder}"
        deleted += _cleanup_folder(storage, folder_path, cutoff)
        _remove_empty_folder(storage, folder_path)
    return deleted


def _cleanup_folder(storage: Storage, path: str, cutoff: datetime) -> int:
    # Another cleanup running at the same time can delete a folder or file after it was listed.
    try:
        _, files = storage.listdir(path)
    except FileNotFoundError:
        return 0
    deleted = 0
    for filename in files:
        file_path = f"{path}/{filename}"
        try:
            if storage.get_modified_time(file_path) < cutoff:
                storage.delete(file_path)
                deleted += 1
        except FileNotFoundError:
            continue
    return deleted


def _remove_empty_folder(storage: Storage, path: str) -> None:
    # Only the filesystem leaves empty folders behind. A folder still holding newer files stays.
    if isinstance(storage, FileSystemStorage):
        with contextlib.suppress(OSError):
            Path(storage.path(path)).rmdir()
