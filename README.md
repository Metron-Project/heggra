# heggra

An htmx-powered file upload widget for Django forms.

## Setup

heggra needs Python 3.14+, Django 6.0+ and htmx 2. Install it with:

```
pip install heggra
```

Add `heggra` to `INSTALLED_APPS`. The [documentation](https://heggra.readthedocs.io/) covers the
rest.

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
