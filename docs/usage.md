# Usage

Use `UploadWidget` for a `FileField` or `ImageField`:

```python
from heggra import UploadWidget


class IssueForm(forms.ModelForm):
    class Meta:
        model = Issue
        fields = ["title", "cover", "script"]
        widgets = {
            "cover": UploadWidget(image=True, max_size=10 * 1024 * 1024),
            "script": UploadWidget(accept=["pdf", "txt"]),
        }
```

Render the form as usual. It must post with `enctype="multipart/form-data"` and include
`{% csrf_token %}`, which the upload request sends along:

```html
<form method="post" enctype="multipart/form-data">
  {% csrf_token %}
  {{ form }}
  <button type="submit">Save</button>
</form>
```

## How an upload works

1. The user picks a file, or drops it on the dropzone. When several files are dropped, only the
   first is kept.
2. htmx posts the file to heggra's upload view at once, and the widget shows a progress bar.
3. The view validates the file and saves it to temporary storage, under a name made safe to store
   and cut to 100 characters, the longest a model `FileField` takes by default. A field with a
   smaller `max_length` refuses longer names when the form is submitted. The widget then shows the
   file's name and size, a preview for images, and a remove button, and holds a signed token for the file
   in a hidden `<name>-token` input. The file input is emptied, so the file isn't sent a second
   time with the form.
4. When the form is submitted, the widget turns the token back into the file, and the form field
   and model field handle it like any other upload.

If JavaScript doesn't run, or the form is submitted before the upload has finished, the file goes up
with the form like any file input, and the widget checks it against its options.

If the form has errors, the widget shows the uploaded file again, so the user doesn't have to pick
it again. A file that went up with the form and passed the widget's checks is shown again too: the
widget saves it to temporary storage when it renders the form again, and holds its token like any
upload.

A file the field itself rejected isn't shown again, as when a validator or the form's
`clean_<field>()` refused it, so it isn't submitted again only to fail the same way. The widget
tells from the `aria-invalid` attribute Django gives a field with errors, and treats any error on
the field as one about the file, except checking the clear checkbox while uploading a file. A form
that adds an error to the field in `clean()` also makes the user pick the file again.

A token that is invalid, has expired, or was issued for a different field, or for the same field
with different options, is refused: the field reports that the file is no longer available and
asks for it again, and an optional field keeps its current file until the form is saved without
errors. Checking the clear checkbox still clears the field.

## Formsets

The widget works in formsets, including forms the page adds by copying the formset's
`empty_form`. Replace `__prefix__` with the new form's index everywhere in the copied HTML, as
Django's formset documentation suggests, not only in `name` and `id` attributes: the file input's
`hx-params` holds its name too. Then have htmx process the new form, with `htmx.process()`, unless
htmx added it itself. The upload view accepts a file whose name matches the empty form's with each
`__prefix__` replaced by a number, and issues its token for the name the form will submit.

## Options

| Argument | Purpose |
| --- | --- |
| `image` | Check that the file is an image Pillow can open, show a preview, and default the input's `accept` to `image/*`. Needs Pillow |
| `max_size` | The largest file allowed, in bytes, at least 1. Larger files are refused in the browser before sending, and again by the server |
| `accept` | The allowed file extensions, with or without the dot and in any case, such as `["pdf", ".TXT"]`. Only a file's last extension is checked, so multi-part extensions such as `tar.gz` aren't allowed: use `gz`. Also sets the input's `accept` attribute |
| `classes` | CSS classes for the widget's elements. See [Styling](styling.md) |
| `attrs` | HTML attributes for the file input, as for any widget |

The upload view checks `max_size`, `accept` and `image`. A file that comes with the form instead,
because JavaScript didn't run or the upload hadn't finished, is checked by the widget against the
same rules, and a file that breaks them is a validation error on the field. Either way, the form
field checks the file again when the form is submitted, so a model `ImageField` still validates the
image and any validators on the field still run.

On an edit form, a field with a file shows it, with a preview for images.

Previews are shown only for images browsers can display: PNG, JPEG, GIF, WebP, AVIF, BMP and ICO.
Other images Pillow opens, such as TIFF or PSD, upload and save the same way, and the widget shows
only their name and size. An uploaded image is recognised by the type Pillow detects, and a
current file by its extension. An optional field also
shows a checkbox to clear it, which works the same as Django's `ClearableFileInput`: checking it
and uploading a new file at the same time is a validation error.

## Changing the text

Subclass the widget to change its text:

| Attribute | Default |
| --- | --- |
| `button_text` | `"Choose a file…"` |
| `drop_text` | `"or drop it here"` |
| `remove_text` | `"Remove"` |
| `too_large_text` | `"The file can't be larger than %(size)s."` |
| `failed_text` | `"The upload failed. Please try again."` |
| `expired_text` | `"The uploaded file is no longer available. Please upload it again."`, for a submitted token that is invalid or has expired |
| `initial_text` | `"Currently"`, before the current file |
| `clear_checkbox_label` | `"Clear"` |

## Translations

heggra's text is marked for translation, and heggra ships catalogs for these languages:

- Italian (`it`)

Nothing needs to be set up beyond Django's usual
[translation settings](https://docs.djangoproject.com/en/stable/topics/i18n/translation/), such as
`LANGUAGES` and `LocaleMiddleware`: Django finds heggra's catalogs because `heggra` is in
`INSTALLED_APPS`. `initial_text` and `clear_checkbox_label` come from Django's
`ClearableFileInput`, so Django's own catalogs translate them.

The widget renders its text in the language active when the form is rendered, and the upload view
renders its errors in the language of the upload's request. With `LocaleMiddleware`, both are the
user's language.

The upload view has three messages of its own, which the widget's attributes don't change:

- `"This page has expired. Reload it to upload files."`, when the page is older than
  `HEGGRA_MAX_AGE`
- `"Log in to upload files."`, when `HEGGRA_LOGIN_REQUIRED` is on and the user isn't logged in
- `"No file was submitted."`

To change one form's text, subclass the widget as above. To change a translation everywhere, or
add one for a language heggra doesn't ship, put entries with the same `msgid` in a catalog in one
of your `LOCALE_PATHS`, which Django reads before an app's catalogs. `makemessages` doesn't extract
strings from installed packages, and marks entries it can't find in your code as obsolete, so keep
these in a directory of their own, compiled with `compilemessages`:

```python
LOCALE_PATHS = [
    BASE_DIR / "locale",  # your project's catalogs, which makemessages writes
    BASE_DIR / "locale_overrides",  # entries for heggra's strings, written by hand
]
```

A translation of heggra into a new language is also welcome as a pull request.

## Cleaning up

Uploads stay in temporary storage after their form is saved, and when a form is never submitted.
The `heggra_cleanup` command deletes those older than `HEGGRA_MAX_AGE` plus an hour, whose tokens no
longer work. The extra hour lets a form that accepted a token just before it expired finish saving.
Run the command on a schedule, such as daily from cron:

```
python manage.py heggra_cleanup
```

Uploads are saved under `heggra/` in the storage named by `HEGGRA_STORAGE`, `"default"` unless set.
See [Security](security.md) before using public storage.
