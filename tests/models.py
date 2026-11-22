from django.db import models


class Document(models.Model):
    title = models.CharField(max_length=100)
    attachment = models.FileField(upload_to="attachments", blank=True)
    cover = models.ImageField(upload_to="covers", blank=True)
