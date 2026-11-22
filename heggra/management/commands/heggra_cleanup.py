"""Delete expired temporary uploads."""

from typing import Any, override

from django.core.management.base import BaseCommand

from heggra.storage import cleanup


class Command(BaseCommand):
    """Delete uploads older than ``HEGGRA_MAX_AGE``, whose tokens no longer work."""

    help = "Delete temporary uploads older than HEGGRA_MAX_AGE."

    @override
    def handle(self, *args: Any, **options: Any) -> None:
        deleted = cleanup()
        self.stdout.write(f"Deleted {deleted} expired upload{'' if deleted == 1 else 's'}.")
