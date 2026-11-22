# JavaScript

`heggra.js` is part of the widget's media. Widgets added to the page later need no setup beyond
htmx processing them.

Each widget dispatches bubbling events on its outer element:

| Event | When | `event.detail` |
| --- | --- | --- |
| `heggra:upload` | A file has uploaded | `name`, the file's name, and `token` |
| `heggra:error` | An upload was refused or failed | `message` |
| `heggra:remove` | The user removed the uploaded file | `name` |

For example, to keep a form's submit button disabled while a file is uploading:

```js
const submit = document.querySelector("#issue-form [type=submit]");
document.addEventListener("htmx:beforeRequest", (event) => {
  if (event.target.matches("[data-heggra-input]")) submit.disabled = true;
});
document.addEventListener("htmx:afterRequest", (event) => {
  if (event.target.matches("[data-heggra-input]")) submit.disabled = false;
});
```
