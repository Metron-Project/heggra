"""The form widget."""

import json
from collections.abc import Iterable, Mapping
from importlib.util import find_spec
from typing import Any, Self, override

from django import forms
from django.conf import settings
from django.core import signing
from django.core.exceptions import ImproperlyConfigured
from django.core.files.uploadedfile import UploadedFile
from django.forms.widgets import FILE_INPUT_CONTRADICTION, CheckboxInput
from django.template.defaultfilters import filesizeformat
from django.urls import reverse
from django.utils.datastructures import MultiValueDict
from django.utils.translation import gettext_lazy as _

from .storage import CONFIG_SALT, Rules, TemporaryUpload, open_token, upload_context


class UploadWidget(forms.ClearableFileInput):
    """File input that uploads a picked or dropped file at once, through htmx.

    ``image=True`` checks that the file is an image Pillow can open and shows a preview.
    ``max_size`` limits the file's size in bytes, and ``accept`` lists the allowed extensions,
    such as ``["pdf", "txt"]``. ``classes`` maps the widget's elements to CSS classes, replacing
    the ``HEGGRA_CLASSES`` setting's value for each key it sets.
    """

    template_name = "heggra/widget.html"
    button_text = _("Choose a file…")
    drop_text = _("or drop it here")
    remove_text = _("Remove")
    too_large_text = _("The file can't be larger than %(size)s.")
    failed_text = _("The upload failed. Please try again.")

    class Media:
        js = ("heggra/heggra.js",)

    def __init__(
        self,
        *,
        image: bool = False,
        max_size: int | None = None,
        accept: Iterable[str] = (),
        classes: dict[str, str] | None = None,
        attrs: dict[str, Any] | None = None,
    ) -> None:
        if image and find_spec("PIL") is None:
            raise ImproperlyConfigured("UploadWidget(image=True) needs Pillow: heggra[image].")
        super().__init__(attrs)
        self.image = image
        self.max_size = max_size
        self.accept = sorted({extension.lower().lstrip(".") for extension in accept})
        self.classes = classes or {}
        # FileField.bound_data hands a bound form's initial value to the widget, so the widget
        # remembers what it read, the way ClearableFileInput remembers its checkbox.
        self.uploads: dict[str, TemporaryUpload] = {}

    @override
    def __deepcopy__(self, memo: dict[int, Any]) -> Self:
        # Widget.__deepcopy__ copies shallowly, which would share uploads between forms.
        widget = super().__deepcopy__(memo)
        widget.uploads = {}
        return widget

    def token_name(self, name: str) -> str:
        """Return the name of the hidden input that submits an upload's token."""
        return f"{name}-token"

    def rules(self, name: str) -> Rules:
        """Return what this widget accepts when rendered as ``name``."""
        return {
            "name": name,
            "max_size": self.max_size,
            "accept": self.accept,
            "image": self.image,
        }

    @override
    def use_required_attribute(self, initial: Any) -> bool:
        # The file input is emptied once its file has uploaded, so only the server can validate.
        return False

    @override
    def value_from_datadict(
        self, data: Mapping[str, Any], files: MultiValueDict[str, UploadedFile], name: str
    ) -> Any:
        # A file in FILES came with the form, when the script didn't run or hadn't finished.
        upload: UploadedFile | None = files.get(name)
        token = data.get(self.token_name(name))
        if upload is None and token and (pending := open_token(token, self.rules(name))):
            upload = self.uploads[name] = pending
        checkbox_name = self.clear_checkbox_name(name)
        self.checked = checkbox_name in data
        if not self.is_required and CheckboxInput().value_from_datadict(data, files, checkbox_name):
            return FILE_INPUT_CONTRADICTION if upload else False
        return upload

    @override
    def value_omitted_from_data(
        self, data: Mapping[str, Any], files: MultiValueDict[str, UploadedFile], name: str
    ) -> bool:
        return super().value_omitted_from_data(data, files, name) and (
            self.token_name(name) not in data
        )

    @override
    def get_context(self, name: str, value: Any, attrs: dict[str, Any] | None) -> dict[str, Any]:
        context = super().get_context(name, value, attrs)
        classes = {**getattr(settings, "HEGGRA_CLASSES", {}), **self.classes}
        widget = context["widget"]
        widget_attrs = widget["attrs"]
        widget_attrs.setdefault("id", f"heggra_{name}")
        widget_attrs["class"] = " ".join(
            filter(None, ["heggra-input", classes.get("input"), widget_attrs.get("class")])
        )
        if self.accept:
            widget_attrs.setdefault("accept", ",".join(f".{ext}" for ext in self.accept))
        elif self.image:
            widget_attrs.setdefault("accept", "image/*")
        # ClearableFileInput puts the checkbox state in attrs, which would land on the file input.
        checkbox_checked = widget_attrs.pop("checked", False)
        disabled = bool(widget_attrs.get("disabled"))

        rules = self.rules(name)
        config = {"rules": rules, "classes": classes, "remove_text": str(self.remove_text)}
        upload = self.uploads.get(name)
        widget.update(
            button_text=self.button_text,
            checkbox_checked=checkbox_checked,
            classes=classes,
            hx_vals=json.dumps(
                {"heggra-config": signing.dumps(config, salt=CONFIG_SALT, compress=True)}
            ),
            disabled=disabled,
            drop_text=self.drop_text,
            error_id=f"{widget_attrs['id']}_error",
            failed_text=self.failed_text,
            file_id=f"{widget_attrs['id']}_file",
            is_image=self.image,
            max_size=self.max_size,
            remove_text=self.remove_text,
            too_large_text=self.max_size
            and self.too_large_text % {"size": filesizeformat(self.max_size)},
            upload=upload
            and upload_context(upload.name or "", upload.size or 0, upload.token, rules),
            upload_url=reverse("heggra:upload"),
        )
        return context
