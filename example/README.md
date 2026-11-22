# heggra example

A small comics catalogue, styled with [Bulma](https://bulma.io/), that uses `UploadWidget` for an
issue's cover image and script. From the repository root:

```
uv sync
uv run example/manage.py migrate
uv run example/manage.py runserver
```

Open http://localhost:8000/ and add or edit an issue. The page loads htmx and Bulma from a CDN, so
it needs a network connection.

## What to look at

| File | Shows |
| --- | --- |
| [`comics/forms.py`](comics/forms.py) | The widget on a required `ImageField` with `image=True` and `max_size`, and on an optional `FileField` with `accept` |
| [`project/settings.py`](project/settings.py) | `HEGGRA_CLASSES` with Bulma's file element classes, and `HEGGRA_STORAGE` pointing at a private storage for uploads |
| [`comics/static/comics/site.css`](comics/static/comics/site.css) | The few styles Bulma has no class for |
| [`comics/templates/comics/issue_form.html`](comics/templates/comics/issue_form.html) | `{{ form.media }}`, the form's `enctype` and `{% csrf_token %}`, and listening for the `heggra:*` events |
| [`project/urls.py`](project/urls.py) | Including `heggra.urls`, and serving saved files while `DEBUG` is on |

Things to try on the issue form:

- Drop an image on the cover field, or click it to pick one. It uploads at once, with a preview.
- Save with the series left empty. The form shows its error and keeps the uploaded cover.
- Drop a file over 1 MB, or a `.zip`, on the script field. The first is refused before uploading,
  the second by the server.
- Edit a saved issue: the current files are shown, and the script has a checkbox to clear it.

Uploads wait in `example/uploads/` until their form is saved, and saved files go to
`example/media/`. To delete uploads older than a day, run `uv run example/manage.py heggra_cleanup`.
To start over, delete `example/db.sqlite3`, `example/media/` and `example/uploads/`, and run
`migrate` again.
