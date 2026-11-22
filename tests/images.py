import io

from django.core.files.uploadedfile import SimpleUploadedFile
from PIL import Image


def png(name="cover.png", size=(4, 4)):
    buffer = io.BytesIO()
    Image.new("RGB", size, "red").save(buffer, "PNG")
    return SimpleUploadedFile(name, buffer.getvalue(), content_type="image/png")
