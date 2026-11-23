# API reference

## Widget

```{eval-rst}
.. autoclass:: heggra.UploadWidget
```

## Settings

`HEGGRA_CLASSES`
: A dict mapping the widget's elements to CSS classes. A widget's `classes=` replaces its value
  for each key it sets. See [Styling](styling.md).

`HEGGRA_STORAGE`
: The alias in `STORAGES` of the storage that holds uploads until their form is saved. Defaults
  to `"default"`. See [Security](security.md#temporary-storage).

`HEGGRA_MAX_AGE`
: How many seconds an upload's token works for. Defaults to `86400`, one day.

`HEGGRA_LOGIN_REQUIRED`
: When `True`, anonymous users can't upload files or view previews. Defaults to `True`. Set it to
  `False` to let anyone who can load a form upload files. See
  [Security](security.md#limiting-uploads).

## URLs

`heggra:upload`
: Takes a widget's file, by POST, and renders it or the reasons it was refused.

`heggra:preview`
: Serves an image upload by its token.

## Management commands

`heggra_cleanup`
: Deletes uploads older than `HEGGRA_MAX_AGE` plus an hour.

## System checks

`heggra.E001`
: `HEGGRA_STORAGE` isn't in `STORAGES`.

`heggra.W001`
: `HEGGRA_LOGIN_REQUIRED` is `True`, as it is by default, but `AuthenticationMiddleware` isn't
  in `MIDDLEWARE`.
