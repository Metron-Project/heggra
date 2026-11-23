# Security

## Tokens

Each upload is referred to by a token signed with `SECRET_KEY`. A token names the field it was
issued for and the rules it was checked against (`max_size`, `accept` and `image`), and the widget
only accepts a token whose rules match its own, so a file checked for one field can't be submitted
to a stricter one. Tokens expire after `HEGGRA_MAX_AGE` seconds, one day by default.

A token isn't tied to a user or session: anyone holding it can submit the file with a form, or view
an image's preview. heggra only ever gives a token to the browser that uploaded the file.

## The upload view

The widget's rules reach the upload view signed, so a client can't loosen them. The signature
expires after `HEGGRA_MAX_AGE`, like a token's, so a copied page can't be used to upload forever,
and a page left open longer than that must be reloaded before uploading. The view is protected by
Django's CSRF check like any other POST, but it accepts uploads from anyone who can load a form.
Set `HEGGRA_LOGIN_REQUIRED = True` to refuse anonymous uploads.

The view checks `max_size` only once Django has received the whole file, and Django's
`DATA_UPLOAD_MAX_MEMORY_SIZE` doesn't cover files. Limit the size of request bodies in your web
server too, for example with nginx's `client_max_body_size`.

## Temporary storage

Uploads are saved as `heggra/<random folder>/<cleaned file name>` in the storage named by
`HEGGRA_STORAGE`. If that storage serves files publicly, as a public bucket or `MEDIA_URL` does,
uploads can be fetched by their URL before any form is saved, although the folder name can't be
guessed. Point `HEGGRA_STORAGE` at a private storage to avoid that:

```python
STORAGES = {
    # ...
    "uploads": {
        "BACKEND": "django.core.files.storage.FileSystemStorage",
        "OPTIONS": {"location": BASE_DIR / "uploads"},
    },
}
HEGGRA_STORAGE = "uploads"
```

Run [`heggra_cleanup`](usage.md#cleaning-up) on a schedule, so abandoned uploads don't build up.

## Previews

The preview view only serves uploads from `image=True` widgets, which Pillow has opened, with the
type Pillow detected, and only when that is a type browsers show: PNG, JPEG, GIF, WebP, AVIF, BMP
or ICO. It sends `X-Content-Type-Options: nosniff` and a sandboxing
`Content-Security-Policy`, so a file can't run script even when opened directly.
