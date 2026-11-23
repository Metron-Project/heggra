import json
from html import unescape

import pytest
from django import forms
from django.core import signing
from django.core.exceptions import ImproperlyConfigured
from django.core.files.uploadedfile import SimpleUploadedFile
from django.utils.datastructures import MultiValueDict

from heggra import UploadWidget, storage

from .forms import DocumentForm
from .images import png
from .models import Document


def text_file(name="notes.txt", content=b"hello"):
    return SimpleUploadedFile(name, content, content_type="text/plain")


def token_for(form, field, file):
    return storage.save_temporary(file, form.fields[field].widget.rules(field))


def config_of(html):
    hx_vals = html.split('hx-vals="')[1].split('"')[0]
    value = json.loads(unescape(hx_vals))["heggra-config"]
    return signing.loads(value, salt=storage.CONFIG_SALT)


def test_rules():
    widget = UploadWidget(max_size=10, accept=[".TXT", "pdf", "txt"])
    assert widget.rules("doc") == {
        "name": "doc",
        "max_size": 10,
        "accept": ["pdf", "txt"],
        "image": False,
    }


def test_image_needs_pillow(monkeypatch):
    monkeypatch.setattr("heggra.widgets.find_spec", lambda name: None)
    with pytest.raises(ImproperlyConfigured, match="Pillow"):
        UploadWidget(image=True)


def test_render():
    html = DocumentForm()["attachment"].as_widget()
    assert 'class="heggra ' in html
    assert 'id="id_attachment"' in html
    assert 'class="heggra-input"' in html
    assert 'accept=".pdf,.txt"' in html
    assert 'hx-post="/heggra/upload/"' in html
    assert 'hx-target="#id_attachment_file"' in html
    assert 'hx-params="attachment,heggra-config,csrfmiddlewaretoken"' in html
    assert 'data-heggra-max-size="1024"' in html
    assert "required" not in html
    assert "checked" not in html
    assert "heggra-current" not in html
    assert config_of(html) == {
        "rules": {"name": "attachment", "max_size": 1024, "accept": ["pdf", "txt"], "image": False},
        "classes": {},
        "remove_text": "Remove",
        "too_large_text": "The file can't be larger than %(size)s.",
    }


def test_too_large_text_reaches_the_upload_view():
    class Widget(UploadWidget):
        too_large_text = "Too big, over %(size)s!"

    assert config_of(Widget(max_size=10).render("doc", None))["too_large_text"] == (
        "Too big, over %(size)s!"
    )


def test_render_image_accepts_images():
    html = DocumentForm()["cover"].as_widget()
    assert 'accept="image/*"' in html
    assert "data-heggra-max-size" not in html


def test_default_id_without_auto_id():
    html = DocumentForm(auto_id=False)["attachment"].as_widget()
    assert 'id="heggra_attachment"' in html


def test_classes_merge_with_settings(settings):
    settings.HEGGRA_CLASSES = {"root": "file", "input": "file-input", "preview": "x"}
    html = DocumentForm()["cover"].as_widget()
    assert 'class="heggra file"' in html
    assert 'class="heggra-input file-input"' in html
    assert config_of(html)["classes"] == {"root": "file", "input": "file-input", "preview": "image"}


def test_prefixed_form():
    html = DocumentForm(prefix="doc")["attachment"].as_widget()
    assert 'hx-params="doc-attachment,heggra-config,csrfmiddlewaretoken"' in html
    assert config_of(html)["rules"]["name"] == "doc-attachment"


@pytest.mark.django_db
def test_render_current_file(media_root):
    document = Document.objects.create(title="A", cover=png())
    html = DocumentForm(instance=document)["cover"].as_widget()
    assert "heggra-current" in html
    assert f'src="{document.cover.url}"' in html
    assert 'name="cover-clear"' in html


def test_render_disabled():
    form = DocumentForm()
    form.fields["attachment"].disabled = True
    assert " disabled" in form["attachment"].as_widget()


def test_value_from_files():
    form = DocumentForm()
    widget = form.fields["attachment"].widget
    file = text_file()
    assert (
        widget.value_from_datadict({}, MultiValueDict({"attachment": [file]}), "attachment") is file
    )


def test_value_from_token():
    form = DocumentForm()
    widget = form.fields["attachment"].widget
    token = token_for(form, "attachment", text_file())
    value = widget.value_from_datadict({"attachment-token": token}, MultiValueDict(), "attachment")
    assert value.read() == b"hello"


def test_token_for_another_field_is_ignored():
    form = DocumentForm()
    token = storage.save_temporary(text_file(), form.fields["cover"].widget.rules("cover"))
    widget = form.fields["attachment"].widget
    assert (
        widget.value_from_datadict({"attachment-token": token}, MultiValueDict(), "attachment")
        is None
    )


def test_clear():
    widget = DocumentForm().fields["attachment"].widget
    data = {"attachment-clear": "on"}
    assert widget.value_from_datadict(data, MultiValueDict(), "attachment") is False


def test_clear_and_upload_contradict():
    form = DocumentForm()
    widget = form.fields["attachment"].widget
    data = {
        "attachment-clear": "on",
        "attachment-token": token_for(form, "attachment", text_file()),
    }
    value = widget.value_from_datadict(data, MultiValueDict(), "attachment")
    assert value is forms.widgets.FILE_INPUT_CONTRADICTION


@pytest.mark.parametrize(
    ("data", "omitted"),
    [({}, True), ({"attachment-token": "x"}, False), ({"attachment-clear": "on"}, False)],
)
def test_value_omitted(data, omitted):
    widget = UploadWidget()
    assert widget.value_omitted_from_data(data, MultiValueDict(), "attachment") is omitted


@pytest.mark.django_db
def test_form_saves_the_upload():
    form = DocumentForm()
    data = {
        "title": "A",
        "attachment-token": token_for(form, "attachment", text_file()),
        "cover-token": token_for(form, "cover", png()),
    }
    form = DocumentForm(data)
    assert form.is_valid(), form.errors
    document = form.save()
    assert document.attachment.name == "attachments/notes.txt"
    assert document.attachment.read() == b"hello"
    assert document.cover.name == "covers/cover.png"
    assert document.cover.width == 4


@pytest.mark.django_db
def test_invalid_form_keeps_the_upload():
    form = DocumentForm()
    token = token_for(form, "cover", png())
    form = DocumentForm({"title": "", "cover-token": token})
    assert not form.is_valid()
    html = form["cover"].as_widget()
    assert f'value="{token}"' in html
    assert 'name="cover-token"' in html
    assert 'class="heggra-preview image"' in html
    assert "cover.png" in html
    assert "data-heggra-remove" in html


@pytest.mark.django_db
def test_clearing_the_current_file(media_root):
    document = Document.objects.create(title="A", attachment=text_file())
    form = DocumentForm({"title": "A", "attachment-clear": "on"}, instance=document)
    assert form.is_valid(), form.errors
    assert not form.save().attachment


@pytest.mark.django_db
def test_clear_checkbox_stays_checked_after_an_error(media_root):
    document = Document.objects.create(title="A", attachment=text_file())
    form = DocumentForm({"title": "", "attachment-clear": "on"}, instance=document)
    assert not form.is_valid()
    html = form["attachment"].as_widget()
    assert 'name="attachment-clear" id="attachment-clear_id" checked' in html


def test_render_without_restrictions():
    assert "accept" not in UploadWidget().render("doc", None)


@pytest.mark.django_db
def test_uploads_are_not_shared_between_forms():
    token = token_for(DocumentForm(), "cover", png())
    form = DocumentForm({"title": "", "cover-token": token})
    assert not form.is_valid()
    assert token in form["cover"].as_widget()
    assert token not in DocumentForm()["cover"].as_widget()
