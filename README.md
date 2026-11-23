# heggra

An htmx-powered file upload widget for Django forms, with drag and drop, that fits any CSS
framework.

## Setup

heggra needs Python 3.14+, Django 6.0+ and htmx 2. Install it with:

```
pip install heggra
```

Use `pip install "heggra[image]"` for image fields. Add `heggra` to `INSTALLED_APPS`, include
`heggra.urls`, and load htmx and `{{ form.media }}` on the page. Then use the widget:

```python
from heggra import UploadWidget


class IssueForm(forms.ModelForm):
    class Meta:
        model = Issue
        fields = ["cover"]
        widgets = {"cover": UploadWidget(image=True)}
```

The [documentation](https://heggra.readthedocs.io/) covers the rest, including styling for Bulma
and other CSS frameworks.

## Development

```
uv sync
uv run pre-commit install
uv run pytest
uv run ruff check .
```

To build the documentation:

```
uv run --group docs sphinx-build -W docs docs/_build/html
```

## License

heggra is released under the GNU General Public License v3.0 or later. See [LICENSE](LICENSE).
