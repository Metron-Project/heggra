// Listeners live on the document, so widgets added to the page later need no setup.
(() => {
  "use strict";

  // An htmx partial can run this script again, which would double every listener.
  if (window.heggraLoaded) return;
  window.heggraLoaded = true;

  const part = (root, name) => root.querySelector(`[data-heggra-${name}]`);
  const rootOf = (element) => element.closest("[data-heggra]");
  const classNames = (value) => (value || "").split(/\s+/).filter(Boolean);
  const isWidgetInput = (element) => element instanceof Element && element.matches("[data-heggra-input]");

  const notify = (root, name, detail) => {
    root.dispatchEvent(new CustomEvent(`heggra:${name}`, { bubbles: true, detail }));
  };

  const setDragging = (root, dragging) => {
    const dropzone = part(root, "dropzone");
    for (const name of classNames(root.dataset.heggraActiveClass)) {
      dropzone.classList.toggle(name, dragging);
    }
  };

  const setProgress = (root, value) => {
    const progress = part(root, "progress");
    const visible = value !== null;
    progress.hidden = !visible;
    progress.style.display = visible ? "" : "none";
    if (visible) progress.value = value;
  };

  const clearError = (root) => part(root, "error").replaceChildren();

  const showError = (root, message) => {
    const error = document.createElement("div");
    error.className = ["heggra-error", ...classNames(root.dataset.heggraErrorClass)].join(" ");
    error.setAttribute("role", "alert");
    error.append(Object.assign(document.createElement("p"), { textContent: message }));
    part(root, "error").replaceChildren(error);
    // The file was refused, so it mustn't go up with the form either.
    part(root, "input").value = "";
    notify(root, "error", { message });
  };

  // Only dropzones of enabled widgets take files, so the page doesn't open dropped files instead.
  const dropzoneOf = (event) => {
    const dropzone = event.target instanceof Element && event.target.closest("[data-heggra-dropzone]");
    if (!dropzone || part(rootOf(dropzone), "input").disabled) return null;
    return dropzone;
  };

  for (const type of ["dragenter", "dragover"]) {
    document.addEventListener(type, (event) => {
      const dropzone = dropzoneOf(event);
      if (!dropzone) return;
      event.preventDefault();
      event.dataTransfer.dropEffect = "copy";
      setDragging(rootOf(dropzone), true);
    });
  }

  document.addEventListener("dragleave", (event) => {
    const dropzone = dropzoneOf(event);
    if (dropzone && !dropzone.contains(event.relatedTarget)) setDragging(rootOf(dropzone), false);
  });

  document.addEventListener("drop", (event) => {
    const dropzone = dropzoneOf(event);
    if (!dropzone) return;
    event.preventDefault();
    const root = rootOf(dropzone);
    setDragging(root, false);
    const [file] = event.dataTransfer.files;
    if (!file) return;
    // The widget holds one file, so only the first of several dropped files is kept.
    const transfer = new DataTransfer();
    transfer.items.add(file);
    const input = part(root, "input");
    input.files = transfer.files;
    input.dispatchEvent(new Event("change", { bubbles: true }));
  });

  // Checked before sending, so an oversized file isn't uploaded only to be refused.
  document.addEventListener("htmx:beforeRequest", (event) => {
    if (!isWidgetInput(event.target)) return;
    const root = rootOf(event.target);
    const [file] = event.target.files;
    if (!file) {
      event.preventDefault();
      return;
    }
    const maxSize = Number(root.dataset.heggraMaxSize);
    if (maxSize && file.size > maxSize) {
      event.preventDefault();
      showError(root, root.dataset.heggraTooLarge);
      return;
    }
    clearError(root);
    setProgress(root, 0);
  });

  document.addEventListener("htmx:xhr:progress", (event) => {
    if (!isWidgetInput(event.target) || !event.detail.lengthComputable) return;
    setProgress(rootOf(event.target), Math.round((event.detail.loaded / event.detail.total) * 100));
  });

  document.addEventListener("htmx:afterRequest", (event) => {
    if (isWidgetInput(event.target)) setProgress(rootOf(event.target), null);
  });

  // The element that sent a request; a swap event's own elt is what was swapped.
  const sender = (event) => event.detail.requestConfig?.elt;

  // htmx drops error responses, but a refused upload carries a message for the user.
  document.addEventListener("htmx:beforeSwap", (event) => {
    if (!isWidgetInput(sender(event))) return;
    const header = (name) => event.detail.xhr.getResponseHeader(name);
    if (header("X-Heggra-Error")) {
      event.detail.shouldSwap = true;
      event.detail.isError = false;
      event.detail.target = part(rootOf(sender(event)), "error");
    } else if (!header("X-Heggra-Upload")) {
      // Something else answered, such as a login page after a redirect: the upload failed.
      event.detail.shouldSwap = false;
      event.detail.isError = true;
    }
  });

  document.addEventListener("htmx:afterSwap", (event) => {
    if (!isWidgetInput(sender(event))) return;
    const root = rootOf(sender(event));
    // The file is on the server now, and its token goes with the form instead.
    part(root, "input").value = "";
    if (event.detail.target.matches("[data-heggra-error]")) {
      notify(root, "error", { message: event.detail.target.textContent.trim() });
      return;
    }
    const upload = part(root, "upload");
    notify(root, "upload", {
      name: part(upload, "file-name").textContent,
      token: upload.querySelector("input[type=hidden]").value,
    });
  });

  const failed = (event) => {
    if (!isWidgetInput(event.target)) return;
    const root = rootOf(event.target);
    showError(root, root.dataset.heggraFailed);
  };
  document.addEventListener("htmx:responseError", failed);
  document.addEventListener("htmx:sendError", failed);

  document.addEventListener("click", (event) => {
    const remove = event.target instanceof Element && event.target.closest("[data-heggra-remove]");
    if (!remove) return;
    const root = rootOf(remove);
    const name = part(root, "file-name").textContent;
    part(root, "file").replaceChildren();
    part(root, "input").focus();
    notify(root, "remove", { name });
  });
})();
