"""The upload and preview endpoints."""

import re
from typing import Any

from django import forms
from django.core import signing
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import UploadedFile
from django.core.validators import FileExtensionValidator
from django.http import (
    FileResponse,
    Http404,
    HttpRequest,
    HttpResponse,
    HttpResponseBadRequest,
)
from django.http.response import HttpResponseBase
from django.shortcuts import render
from django.template.defaultfilters import filesizeformat
from django.utils.translation import gettext as _
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_GET, require_POST

from .storage import (
    CONFIG_SALT,
    Rules,
    get_login_required,
    get_max_age,
    get_storage,
    has_preview,
    load_token,
    save_temporary,
    upload_context,
)


def _login_required(request: HttpRequest) -> bool:
    return get_login_required() and not request.user.is_authenticated


def _error(
    request: HttpRequest, config: dict[str, Any], messages: list[str], status: int
) -> HttpResponse:
    context = {"classes": config.get("classes", {}), "messages": messages}
    response = render(request, "heggra/error.html", context, status=status)
    # heggra.js swaps only responses with this header, so error pages never land in the widget.
    response.headers["X-Heggra-Error"] = "true"
    return response


def too_large_message(text: str, max_size: int) -> str:
    """Return ``text`` with its ``%(size)s`` placeholder replaced by ``max_size``, made readable.

    A text that isn't a valid format string, such as one with a single ``%``, gets only its
    placeholder replaced, rather than failing every page that renders the widget.
    """
    size = filesizeformat(max_size)
    try:
        return text % {"size": size}
    except KeyError, TypeError, ValueError:
        return text.replace("%(size)s", size)


def validate(file: UploadedFile, rules: Rules, too_large_text: str | None = None) -> list[str]:
    """Return the reasons ``file`` breaks ``rules``, or an empty list if it doesn't.

    ``too_large_text`` is the message for a file over ``max_size``, with a ``%(size)s``
    placeholder, such as a widget's ``too_large_text``.
    """
    max_size = rules["max_size"]
    if max_size is not None and (file.size or 0) > max_size:
        text = too_large_text or _("The file can't be larger than %(size)s.")
        return [too_large_message(text, max_size)]
    field = forms.ImageField() if rules["image"] else forms.FileField()
    if rules["accept"]:
        field.validators.append(FileExtensionValidator(rules["accept"]))
    try:
        field.clean(file)
    except ValidationError as error:
        return error.messages
    return []


def _posted_name(request: HttpRequest, name: str) -> str:
    """Return the name the widget's file was posted under, which is ``name`` unless it's renamed.

    A formset's empty form renders names with ``__prefix__``, which the page replaces with a form's
    index when it adds the form, but it can't change the name signed in the widget's config.
    """
    if "__prefix__" not in name:
        return name
    pattern = re.compile(re.escape(name).replace("__prefix__", r"\d+"))
    return next((posted for posted in request.FILES if pattern.fullmatch(posted)), name)


@never_cache
@require_POST
def upload(request: HttpRequest) -> HttpResponse:
    """Save the file a widget posted and render it, ready to be submitted with the form."""
    # A config expires like a token, so one copied from a page doesn't allow uploads forever.
    try:
        config = signing.loads(
            request.POST.get("heggra-config", ""), salt=CONFIG_SALT, max_age=get_max_age()
        )
    except signing.SignatureExpired:
        return _error(request, {}, [_("This page has expired. Reload it to upload files.")], 400)
    except signing.BadSignature:
        return HttpResponseBadRequest()
    if _login_required(request):
        return _error(request, config, [_("Log in to upload files.")], 403)

    rules: Rules = config["rules"]
    # The token is bound to the name the form will submit it under.
    rules["name"] = _posted_name(request, rules["name"])
    file = request.FILES.get(rules["name"])
    if file is None:
        return _error(request, config, [_("No file was submitted.")], 422)
    messages = validate(file, rules, config.get("too_large_text"))
    if messages:
        return _error(request, config, messages, 422)

    # The stored file's name is cleaned, and the widget shows the name the form will save.
    saved = save_temporary(file, rules)
    context = {
        "classes": config["classes"],
        "remove_text": config["remove_text"],
        "upload": upload_context(
            saved.name or "", saved.size or 0, saved.token, rules, saved.content_type
        ),
    }
    response = render(request, "heggra/file.html", context)
    # heggra.js swaps only responses with this header, so a login page a redirect led to doesn't.
    response.headers["X-Heggra-Upload"] = "true"
    return response


@require_GET
def preview(request: HttpRequest, token: str) -> HttpResponseBase:
    """Serve an image upload, so the widget can show it before the form is saved."""
    payload = load_token(token)
    if payload is None or _login_required(request):
        raise Http404
    content_type = payload["type"]
    # Only files Pillow accepted as images that browsers can show are served, under the type it
    # detected.
    if not has_preview(payload["rules"], content_type):
        raise Http404
    storage = get_storage()
    # Object storages open files lazily, so a missing one would only fail once streaming.
    if not storage.exists(payload["path"]):
        raise Http404
    try:
        content = storage.open(payload["path"], "rb")
    except FileNotFoundError:
        raise Http404 from None
    response = FileResponse(content, content_type=content_type, filename=payload["name"])
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["Content-Security-Policy"] = "default-src 'none'; sandbox"
    response.headers["Cache-Control"] = "private, max-age=3600"
    return response
