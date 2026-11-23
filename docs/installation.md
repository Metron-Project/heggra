# Installation

heggra needs Python 3.14+, Django 6.0+ and htmx 2. Install it with:

```
pip install heggra
```

For image fields, which heggra checks and previews with Pillow, install the `image` extra:

```
pip install "heggra[image]"
```

Add `heggra` to `INSTALLED_APPS`, include its URLs, and load htmx and the form's media on the page:

```python
# urls.py
urlpatterns = [
    path("heggra/", include("heggra.urls")),
]
```

```html
<script src="{% static 'htmx.min.js' %}"></script>
{{ form.media }}
```

Only logged-in users can upload files by default, which needs `django.contrib.auth` and its
`AuthenticationMiddleware`. For forms anyone can fill in, set `HEGGRA_LOGIN_REQUIRED = False`, and
read [Limiting uploads](security.md#limiting-uploads) first.

Uploads wait in temporary storage until their form is saved, so schedule the
[cleanup command](usage.md#cleaning-up) to run regularly.
