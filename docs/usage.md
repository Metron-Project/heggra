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

If the form has errors, the widget shows the uploaded file again, so the user doesn't have to pick
it again. If JavaScript doesn't run, or the form is submitted before the upload has finished, the
file goes up with the form like any file input.

A token that is invalid, has expired, or was issued for a different field counts as no file: a
required field reports that it is required, and an optional field keeps its current file.

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

On an edit form, a field with a file shows it, with a preview for images. An optional field also
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
| `initial_text` | `"Currently"`, before the current file |
| `clear_checkbox_label` | `"Clear"` |

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
