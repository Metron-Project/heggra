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
Django's CSRF check like any other POST, and only logged-in users can upload unless
`HEGGRA_LOGIN_REQUIRED` is `False`.

## Limiting uploads

The upload view saves a file before any form is submitted, so whoever can upload can fill
temporary storage. By default that is only logged-in users. With `HEGGRA_LOGIN_REQUIRED = False`,
it is anyone who can load a page with the widget: the signed config a page carries can't be tied
to a visitor, because anyone can load the page for a new one. heggra doesn't limit how many files a
client uploads, so on a site that lets anyone upload:

- Give every widget a `max_size`. Without one, a file can be as large as your web server allows.
- Limit the size of request bodies in your web server, for example with nginx's
  `client_max_body_size`. The view checks `max_size` only once Django has received the whole file,
  and Django's `DATA_UPLOAD_MAX_MEMORY_SIZE` doesn't cover files.
- Rate-limit `POST` requests to the upload URL, in your web server or a middleware, for example
  per IP address.
- Run `heggra_cleanup` often, such as hourly, and consider a shorter `HEGGRA_MAX_AGE`, so refused
  and abandoned uploads leave sooner. Uploads stay for `HEGGRA_MAX_AGE` plus an hour, and pages
  left open longer than `HEGGRA_MAX_AGE` must be reloaded before uploading.
- Point `HEGGRA_STORAGE` at a storage with a quota, or on its own disk or bucket, so a full
  temporary storage can't stop the rest of the site saving files.

The web server body limit and `max_size` apply when only logged-in users can upload, too.

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
