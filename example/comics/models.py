"""A small comics catalogue with files to upload."""

from django.db import models
from django.urls import reverse


class Issue(models.Model):
    """A single issue of a series, with a cover image and an optional script."""

    series = models.CharField(max_length=100)
    number = models.CharField(max_length=10)
    cover = models.ImageField(upload_to="covers")
    script = models.FileField(upload_to="scripts", blank=True)

    class Meta:
        ordering = ["series", "number"]

    def __str__(self) -> str:
        return f"{self.series} #{self.number}"

    def get_absolute_url(self) -> str:
        """Return the page that edits this issue."""
        return reverse("issue-update", args=[self.pk])
