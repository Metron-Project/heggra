# Styling

heggra brings no styles of its own. Every element has a stable `heggra-*` class, and state is
exposed through `hidden` and the `heggra-dragover` class on the dropzone while a file is dragged
over it. Add your framework's classes with the `HEGGRA_CLASSES` setting, or with `classes=` on a
widget, which replaces the setting's value for each key it sets.

| Key | Element |
| --- | --- |
| `root` | The widget's outer `<div>` |
| `current` | The current file on an edit form |
| `preview` | The `<img>` preview of an image, current or uploaded |
| `clear` | The `<label>` around the clear checkbox |
| `dropzone` | The `<div>` that takes dropped files |
| `dropzone_active` | Added to the dropzone while a file is dragged over it |
| `label` | The `<label>` around the file input |
| `input` | The file input |
| `button` | The `<span>` that reads "Choose a file…" |
| `hint` | The `<span>` that reads "or drop it here" |
| `progress` | The `<progress>` bar |
| `error` | The message shown when an upload is refused |
| `file` | The uploaded file |
| `file_name` | The uploaded file's name |
| `file_size` | The uploaded file's size |
| `remove` | The button that removes the uploaded file |

## Bulma

Bulma's [file upload](https://bulma.io/documentation/form/file/) element has the same structure,
with the file input inside its label:

```python
HEGGRA_CLASSES = {
    "dropzone": "file is-boxed",
    "dropzone_active": "is-primary",
    "label": "file-label",
    "input": "file-input",
    "button": "file-cta",
    "hint": "help",
    "progress": "progress is-small is-primary",
    "error": "help is-danger",
    "file": "box",
    "file_name": "has-text-weight-semibold",
    "remove": "button is-small",
    "preview": "image is-128x128",
    "clear": "checkbox",
}
```

## Without a framework

Without any CSS, the widget shows the browser's own file input with its text beside it, and the
row they sit in takes dropped files. Include the optional `heggra/layout.css` for a dashed dropzone, a
hidden file input that keeps keyboard focus visible, and a bounded preview:

```html
<link rel="stylesheet" href="{% static 'heggra/layout.css' %}">
```

All of its rules are inside `:where()`, so any class from `HEGGRA_CLASSES` overrides them whatever
order the stylesheets load in. It reads these custom properties:

```css
:root {
  --heggra-border-color: #b5b5b5;   /* The dropzone's border, GrayText by default */
  --heggra-active-color: #485fc7;   /* Its border while dragging, and the focus ring */
  --heggra-preview-size: 8rem;      /* The preview's largest width and height */
}
```

## Templates

For bigger changes, override `heggra/widget.html`, `heggra/file.html` (the uploaded file) or
`heggra/error.html` (a refused upload's message). Overriding `heggra/widget.html` from a
project-level template directory requires
`FORM_RENDERER = "django.forms.renderers.TemplatesSetting"`. Keep the `data-heggra-*` attributes,
which `heggra.js` relies on.
