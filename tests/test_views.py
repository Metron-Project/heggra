import pytest
from django.contrib.auth.models import User
from django.core import signing
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse

from heggra import storage

from .images import png

UPLOAD_URL = "/heggra/upload/"


def make_config(**rules):
    rules = {"name": "attachment", "max_size": None, "accept": [], "image": False, **rules}
    config = {"rules": rules, "classes": {"file": "box", "error": "help"}, "remove_text": "Drop"}
    return signing.dumps(config, salt=storage.CONFIG_SALT, compress=True)


def post(client, file, **rules):
    name = rules.get("name", "attachment")
    return client.post(UPLOAD_URL, {"heggra-config": make_config(**rules), name: file})


def text_file(name="notes.txt", content=b"hello"):
    return SimpleUploadedFile(name, content, content_type="text/plain")


def test_upload_renders_the_file(client):
    response = post(client, text_file())
    assert response.status_code == 200
    html = response.content.decode()
    assert 'class="heggra-file box"' in html
    assert "notes.txt" in html
    assert ">Drop</button>" in html
    assert "<img" not in html
    token = html.split('name="attachment-token" value="')[1].split('"')[0]
    rules = {"name": "attachment", "max_size": None, "accept": [], "image": False}
    assert storage.open_token(token, rules).read() == b"hello"


def test_upload_shows_the_name_the_form_saves(client):
    html = post(client, text_file("my notes (1).txt")).content.decode()
    assert "my_notes_1.txt" in html
    assert "my notes" not in html


def test_upload_without_a_usable_name(client):
    response = post(client, text_file("@@@"))
    assert response.status_code == 200
    assert "upload" in response.content.decode()


def test_upload_is_not_cached(client):
    assert "no-cache" in post(client, text_file()).headers["Cache-Control"]


def test_get_is_not_allowed(client):
    assert client.get(UPLOAD_URL).status_code == 405


@pytest.mark.parametrize("config", ["", "tampered"])
def test_bad_config(client, config):
    response = client.post(UPLOAD_URL, {"heggra-config": config, "attachment": text_file()})
    assert response.status_code == 400
    assert "X-Heggra-Error" not in response.headers


def assert_error(response, status, message):
    assert response.status_code == status
    assert response.headers["X-Heggra-Error"] == "true"
    html = response.content.decode()
    assert 'class="heggra-error help" role="alert"' in html
    assert message in html


def test_missing_file(client):
    response = client.post(UPLOAD_URL, {"heggra-config": make_config()})
    assert_error(response, 422, "No file was submitted.")


def test_file_too_large(client):
    response = post(client, text_file(content=b"x" * 2048), max_size=1024)
    assert_error(response, 422, "The file can&#x27;t be larger than 1.0\xa0KB.")


def test_file_too_large_uses_the_widget_text(client):
    rules = {"name": "attachment", "max_size": 1024, "accept": [], "image": False}
    config = {
        "rules": rules,
        "classes": {"error": "help"},
        "remove_text": "Drop",
        "too_large_text": "Max %(size)s",
    }
    data = {
        "heggra-config": signing.dumps(config, salt=storage.CONFIG_SALT, compress=True),
        "attachment": text_file(content=b"x" * 2048),
    }
    assert_error(client.post(UPLOAD_URL, data), 422, "Max 1.0\xa0KB")


def test_file_at_the_size_limit(client):
    assert post(client, text_file(content=b"x" * 1024), max_size=1024).status_code == 200


def test_extension_not_accepted(client):
    response = post(client, text_file("notes.exe"), accept=["txt"])
    assert_error(response, 422, "File extension “exe” is not allowed.")


def test_empty_file(client):
    response = post(client, text_file(content=b""))
    assert_error(response, 422, "The submitted file is empty.")


def test_image_that_is_not_an_image(client):
    response = post(client, text_file("cover.png"), image=True)
    assert_error(response, 422, "Upload a valid image.")


def test_image_upload_has_a_preview(client):
    response = post(client, png(), image=True)
    assert response.status_code == 200
    html = response.content.decode()
    token = html.split('name="attachment-token" value="')[1].split('"')[0]
    assert f'src="{reverse("heggra:preview", args=[token])}"' in html


def test_login_required(client, settings):
    settings.HEGGRA_LOGIN_REQUIRED = True
    assert_error(post(client, text_file()), 403, "Log in to upload files.")


@pytest.mark.django_db
def test_login_required_lets_users_upload(client, settings):
    settings.HEGGRA_LOGIN_REQUIRED = True
    client.force_login(User.objects.create_user("reader"))
    assert post(client, text_file()).status_code == 200


def image_token(file=None, **rules):
    rules = {"name": "cover", "max_size": None, "accept": [], "image": True, **rules}
    file = file or png()
    file.content_type = "image/png"
    return storage.save_temporary(file, rules).token


def test_preview(client):
    response = client.get(reverse("heggra:preview", args=[image_token()]))
    assert response.status_code == 200
    assert response["Content-Type"] == "image/png"
    assert response["X-Content-Type-Options"] == "nosniff"
    assert response["Content-Security-Policy"] == "default-src 'none'; sandbox"
    assert response["Content-Disposition"].startswith("inline")
    assert b"".join(response.streaming_content).startswith(b"\x89PNG")


def test_preview_bad_token(client):
    assert client.get(reverse("heggra:preview", args=["bad"])).status_code == 404


def test_preview_of_a_file_that_is_not_an_image(client):
    rules = {"name": "attachment", "max_size": None, "accept": [], "image": False}
    token = storage.save_temporary(text_file(), rules).token
    assert client.get(reverse("heggra:preview", args=[token])).status_code == 404


def test_preview_without_an_image_type(client):
    file = text_file("cover.png")
    token = storage.save_temporary(
        file, {"name": "cover", "max_size": None, "accept": [], "image": True}
    ).token
    assert client.get(reverse("heggra:preview", args=[token])).status_code == 404


def test_preview_of_a_deleted_file(client):
    token = image_token()
    storage.get_storage().delete(storage.load_token(token)["path"])
    assert client.get(reverse("heggra:preview", args=[token])).status_code == 404


def test_preview_login_required(client, settings):
    settings.HEGGRA_LOGIN_REQUIRED = True
    assert client.get(reverse("heggra:preview", args=[image_token()])).status_code == 404
