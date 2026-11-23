from django.core.files.storage import InMemoryStorage

from heggra import storage


class ObjectStorage(InMemoryStorage):
    """A storage where heggra's folder doesn't exist, like a prefix on S3."""

    def exists(self, name):
        return name != storage.TEMP_DIR and super().exists(name)


class MissingObjectError(Exception):
    """A storage's own error for a missing file, such as boto's ClientError."""


class LazyFile:
    def read(self, *args):
        raise MissingObjectError

    def close(self):
        pass


class LazyStorage(InMemoryStorage):
    """A storage that, like S3's, opens a missing file without noticing it's missing."""

    def _open(self, name, mode="rb"):
        if not self.exists(name):
            return LazyFile()
        return super()._open(name, mode)

    def size(self, name):
        if not self.exists(name):
            raise MissingObjectError
        return super().size(name)
