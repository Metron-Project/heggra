import io

from django.core.files.uploadedfile import SimpleUploadedFile
from PIL import Image


def png(name="cover.png", size=(4, 4)):
    return image(name, "PNG", size)


def image(name, image_format, size=(4, 4)):
    """Return an image file in ``image_format``, as the browser sends it, without its real type."""
    buffer = io.BytesIO()
    Image.new("RGB", size, "red").save(buffer, image_format)
    return SimpleUploadedFile(name, buffer.getvalue(), content_type="image/png")
