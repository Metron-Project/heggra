import ast
import gettext
from html import unescape
from pathlib import Path

import pytest
from django.core import signing
from django.core.files.uploadedfile import SimpleUploadedFile
from django.utils import translation

import heggra
from heggra import UploadWidget, storage

LOCALE = Path(heggra.__file__).parent / "locale"
LANGUAGES = sorted(path.name for path in LOCALE.iterdir() if path.is_dir())


def read_po(path):
    """Return a .po file's translations and the msgids marked fuzzy, ignoring its header."""
    entries, fuzzy = {}, set()
    entry, key, flags = {}, None, ""

    def finish():
        if entry.get("msgid"):
            entries[entry["msgid"]] = entry.get("msgstr", "")
            if "fuzzy" in flags:
                fuzzy.add(entry["msgid"])

    for line in [*path.read_text().splitlines(), ""]:
        if not line.strip():
            finish()
            entry, key, flags = {}, None, ""
        elif line.startswith("#,"):
            flags += line
        elif line.startswith('"'):
            entry[key] += ast.literal_eval(line)
        elif not line.startswith("#"):
            key, value = line.split(" ", 1)
            entry[key] = ast.literal_eval(value)
    return entries, fuzzy


def test_italian_is_shipped():
    assert "it" in LANGUAGES


@pytest.mark.parametrize("language", LANGUAGES)
def test_catalog_is_complete(language):
    entries, fuzzy = read_po(LOCALE / language / "LC_MESSAGES" / "django.po")
    assert entries
    assert not fuzzy
    assert [msgid for msgid, msgstr in entries.items() if not msgstr] == []


@pytest.mark.parametrize("language", LANGUAGES)
def test_compiled_catalog_is_up_to_date(language):
    # Django reads only the .mo, so one left behind by an edit to the .po goes unnoticed.
    messages = LOCALE / language / "LC_MESSAGES"
    entries, _ = read_po(messages / "django.po")
    with (messages / "django.mo").open("rb") as mo:
        compiled = gettext.GNUTranslations(mo)._catalog  # type: ignore[attr-defined]
    assert {msgid: msgstr for msgid, msgstr in compiled.items() if msgid} == entries


def config_of(html):
    value = html.split('"heggra-config": "')[1].split('"')[0]
    return signing.loads(value, salt=storage.CONFIG_SALT)


def test_widget_renders_in_italian():
    with translation.override("it"):
        html = unescape(UploadWidget(max_size=2048).render("doc", None))
    assert "Scegli un file…" in html
    assert "o trascinalo qui" in html
    assert 'data-heggra-too-large="Il file non può superare 2,0\xa0KB."' in html
    assert "Il caricamento non è riuscito. Riprova." in html
    config = config_of(html)
    assert config["remove_text"] == "Rimuovi"
    assert config["too_large_text"] == "Il file non può superare %(size)s."


def test_expired_upload_in_italian():
    widget = UploadWidget()
    with translation.override("it"):
        value = widget.value_from_datadict({"doc-token": "gone"}, {}, "doc")
    assert value.messages == ["Il file caricato non è più disponibile. Caricalo di nuovo."]


def test_upload_view_errors_in_italian(client, settings):
    settings.HEGGRA_LOGIN_REQUIRED = True
    config = {"rules": {"name": "doc", "max_size": None, "accept": [], "image": False}}
    data = {
        "heggra-config": signing.dumps(config, salt=storage.CONFIG_SALT, compress=True),
        "doc": SimpleUploadedFile("notes.txt", b"hello"),
    }
    with translation.override("it"):
        response = client.post("/heggra/upload/", data)
    assert response.status_code == 403
    assert "Accedi per caricare i file." in response.content.decode()
