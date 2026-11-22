# Development

```
uv sync
uv run pre-commit install
uv run pytest
uv run ruff check .
```

To build this documentation:

```
uv run --group docs sphinx-build -W docs docs/_build/html
```

## License

heggra is released under the GNU General Public License v3.0 or later. See
[LICENSE](https://github.com/Metron-Project/heggra/blob/main/LICENSE).
