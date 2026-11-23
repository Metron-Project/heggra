"""Delete expired temporary uploads."""

from typing import Any, override

from django.core.management.base import BaseCommand

from heggra.storage import cleanup


class Command(BaseCommand):
    """Delete uploads whose tokens stopped working over an hour ago."""

    help = "Delete temporary uploads older than HEGGRA_MAX_AGE plus an hour."

    @override
    def handle(self, *args: Any, **options: Any) -> None:
        deleted = cleanup()
        self.stdout.write(f"Deleted {deleted} expired upload{'' if deleted == 1 else 's'}.")
