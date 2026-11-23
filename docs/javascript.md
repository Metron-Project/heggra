# JavaScript

`heggra.js` is part of the widget's media. Widgets added to the page later need no setup beyond
htmx processing them.

The widget works inside an element with htmx attributes of its own, such as a form with
`hx-post` and `hx-select`. Its file input sets, or turns off, each inherited attribute that would
change how an upload is sent or shown: `hx-target`, `hx-swap`, `hx-sync`, `hx-encoding`,
`hx-params`, `hx-select`, `hx-select-oob`, `hx-confirm`, `hx-prompt`, `hx-indicator`,
`hx-disabled-elt`, `hx-push-url` and `hx-replace-url`. It also ignores the `json-enc` extension,
which can't send files.

Each widget dispatches bubbling events on its outer element:

| Event | When | `event.detail` |
| --- | --- | --- |
| `heggra:upload` | A file has uploaded | `name`, the file's name, and `token` |
| `heggra:error` | An upload was refused or failed | `message` |
| `heggra:remove` | The user removed the uploaded file | `name` |

For example, to keep a form's submit button disabled while a file is uploading:

```js
const submit = document.querySelector("#issue-form [type=submit]");
document.addEventListener("htmx:beforeSend", (event) => {
  if (event.target.matches("[data-heggra-input]")) submit.disabled = true;
});
document.addEventListener("htmx:afterRequest", (event) => {
  if (event.target.matches("[data-heggra-input]")) submit.disabled = false;
});
```

Listen for `htmx:beforeSend` rather than `htmx:beforeRequest`: heggra.js cancels the request for a
file over `max_size`, and a cancelled request never sends `htmx:afterRequest`.
