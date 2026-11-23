"""Tests for heggra.js, run in headless Firefox against a live server."""

import shutil
import time

import pytest
from selenium import webdriver
from selenium.common.exceptions import StaleElementReferenceException
from selenium.webdriver.common.by import By
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.support.ui import WebDriverWait

from heggra import views

from .images import png

pytestmark = [
    pytest.mark.skipif(not shutil.which("firefox"), reason="Firefox is not installed"),
    pytest.mark.django_db(transaction=True),
]

# Records the widget's events, so tests can check what the page was told.
RECORD_EVENTS = """
window.heggraEvents = [];
for (const name of ["upload", "error", "remove"]) {
  document.addEventListener(`heggra:${name}`, (event) => {
    window.heggraEvents.push({ type: name, ...event.detail });
  });
}
"""

DROP = """
const [dropzone, name, content, type] = arguments;
const transfer = new DataTransfer();
transfer.items.add(new File([content], name, { type }));
const fire = (kind) => dropzone.dispatchEvent(
  new DragEvent(kind, { bubbles: true, cancelable: true, dataTransfer: transfer })
);
fire("dragenter");
fire("dragover");
window.heggraDragging = dropzone.classList.contains("heggra-dragover");
// dispatchEvent is false when a listener prevented the browser opening the file.
window.heggraDropHandled = !fire("drop");
"""


class Widget:
    def __init__(self, driver, field, element_id=None):
        self.driver = driver
        self.input = driver.find_element(By.ID, element_id or f"id_{field}")
        self.root = self.input.find_element(By.XPATH, "ancestor::*[@data-heggra]")
        self.dropzone = self.root.find_element(By.CSS_SELECTOR, "[data-heggra-dropzone]")
        self.slot = self.root.find_element(By.CSS_SELECTOR, "[data-heggra-file]")
        self.error = self.root.find_element(By.CSS_SELECTOR, "[data-heggra-error]")
        # Navigating can make an element stale between finding it and reading it.
        self.wait = WebDriverWait(driver, 5, ignored_exceptions=[StaleElementReferenceException])

    @property
    def file_name(self):
        names = self.slot.find_elements(By.CSS_SELECTOR, "[data-heggra-file-name]")
        return names[0].text if names else None

    @property
    def token(self):
        tokens = self.slot.find_elements(By.CSS_SELECTOR, "input[type=hidden]")
        return tokens[0].get_attribute("value") if tokens else None

    def pick(self, path):
        self.input.send_keys(str(path))
        self.wait.until(lambda _: self.file_name or self.error.text)

    def drop(self, name, content, content_type="text/plain"):
        self.driver.execute_script(DROP, self.dropzone, name, content, content_type)


@pytest.fixture(scope="module")
def driver():
    options = Options()
    options.add_argument("-headless")
    driver = webdriver.Firefox(options=options)
    yield driver
    driver.quit()


@pytest.fixture
def page(driver, live_server):
    driver.get(f"{live_server.url}/form/")
    WebDriverWait(driver, 5).until(lambda _: driver.execute_script("return !!window.htmx"))
    driver.execute_script(RECORD_EVENTS)
    return driver


def events(page):
    return page.execute_script("return window.heggraEvents")


def write(tmp_path, name, content):
    path = tmp_path / name
    path.write_bytes(content)
    return path


def test_pick_a_file(page, tmp_path):
    widget = Widget(page, "attachment")
    widget.pick(write(tmp_path, "notes.txt", b"hello"))
    assert widget.file_name == "notes.txt"
    assert widget.token
    assert widget.input.get_property("value") == ""
    assert events(page) == [{"type": "upload", "name": "notes.txt", "token": widget.token}]


def test_drop_a_file(page):
    widget = Widget(page, "attachment")
    widget.drop("dropped.txt", "hello")
    widget.wait.until(lambda _: widget.file_name)
    assert widget.file_name == "dropped.txt"
    assert page.execute_script("return window.heggraDragging")
    assert page.execute_script("return window.heggraDropHandled")
    assert "heggra-dragover" not in widget.dropzone.get_attribute("class")


def test_disabled_widget_ignores_drops(page):
    widget = Widget(page, "attachment")
    page.execute_script("arguments[0].disabled = true", widget.input)
    widget.drop("dropped.txt", "hello")
    assert page.execute_script("return window.heggraDropHandled")
    assert not page.execute_script("return window.heggraDragging")
    time.sleep(0.5)
    assert widget.file_name is None
    assert events(page) == []


def test_dragleave_resets_the_dropzone(page):
    widget = Widget(page, "attachment")
    page.execute_script(
        "const zone = arguments[0];"
        "zone.dispatchEvent(new DragEvent('dragover', {bubbles: true, cancelable: true,"
        " dataTransfer: new DataTransfer()}));"
        "zone.dispatchEvent(new DragEvent('dragleave', {bubbles: true,"
        " relatedTarget: document.body}));",
        widget.dropzone,
    )
    assert "heggra-dragover" not in widget.dropzone.get_attribute("class")


def test_too_large_is_refused_before_uploading(page):
    widget = Widget(page, "attachment")
    widget.drop("big.txt", "x" * 2048)
    widget.wait.until(lambda _: widget.error.text)
    message = "The file can't be larger than 1.0\xa0KB."
    assert widget.error.text == message.replace("\xa0", " ")
    assert widget.file_name is None
    assert events(page) == [{"type": "error", "message": message}]


# The snippet in docs/javascript.md.
DISABLE_SUBMIT = """
const submit = document.querySelector("#form [type=submit]");
document.addEventListener("htmx:beforeSend", (event) => {
  if (event.target.matches("[data-heggra-input]")) submit.disabled = true;
});
document.addEventListener("htmx:afterRequest", (event) => {
  if (event.target.matches("[data-heggra-input]")) submit.disabled = false;
});
"""


def test_documented_submit_snippet_survives_a_refused_file(page):
    page.execute_script(DISABLE_SUBMIT)
    submit = page.find_element(By.ID, "submit")
    widget = Widget(page, "attachment")
    widget.drop("big.txt", "x" * 2048)
    widget.wait.until(lambda _: widget.error.text)
    assert submit.is_enabled()
    widget.drop("notes.txt", "hello")
    widget.wait.until(lambda _: widget.file_name == "notes.txt")
    assert submit.is_enabled()


def test_server_errors_are_shown(page):
    widget = Widget(page, "attachment")
    widget.drop("notes.exe", "hello")
    widget.wait.until(lambda _: widget.error.text)
    assert "is not allowed" in widget.error.text
    assert widget.error.find_element(By.CSS_SELECTOR, "[role=alert]")


def test_a_page_that_is_not_an_upload_is_not_shown(page):
    widget = Widget(page, "attachment")
    # As when a login middleware redirects an expired session's upload to its login page.
    page.execute_script(
        "arguments[0].setAttribute('hx-post', '/login/'); htmx.process(arguments[0]);",
        widget.input,
    )
    widget.drop("notes.txt", "hello")
    widget.wait.until(lambda _: widget.error.text)
    assert widget.error.text == "The upload failed. Please try again."
    assert widget.slot.text == ""
    assert events(page) == [{"type": "error", "message": "The upload failed. Please try again."}]


def test_remove_cancels_an_upload_on_its_way(page, monkeypatch):
    widget = Widget(page, "attachment")
    widget.drop("notes.txt", "hello")
    widget.wait.until(lambda _: widget.file_name == "notes.txt")
    save = views.save_temporary
    monkeypatch.setattr(views, "save_temporary", lambda *args: time.sleep(1) or save(*args))
    widget.drop("other.txt", "hello")
    widget.slot.find_element(By.CSS_SELECTOR, "[data-heggra-remove]").click()
    progress = widget.root.find_element(By.CSS_SELECTOR, "[data-heggra-progress]")
    widget.wait.until(lambda _: not progress.is_displayed())
    time.sleep(1.5)
    assert widget.file_name is None
    assert [event["type"] for event in events(page)] == ["upload", "remove"]
    # The cancelled upload's file mustn't go up with the form either.
    assert widget.input.get_property("value") == ""


def test_htmx_attributes_of_the_form_are_not_inherited(page, live_server):
    page.execute_script(
        "const form = document.getElementById('form');"
        "form.setAttribute('hx-post', '/form/');"
        "form.setAttribute('hx-select', '#nothing');"
        "form.setAttribute('hx-select-oob', '#nothing');"
        "form.setAttribute('hx-confirm', 'Sure?');"
        "form.setAttribute('hx-push-url', 'true');"
        "form.setAttribute('hx-disabled-elt', 'find input');"
        "htmx.process(form);"
    )
    widget = Widget(page, "attachment")
    widget.drop("notes.txt", "hello")
    widget.wait.until(lambda _: widget.file_name == "notes.txt")
    assert widget.token
    assert page.current_url == f"{live_server.url}/form/"
    assert widget.input.is_enabled()


def test_ids_with_selector_characters(page, live_server):
    page.get(f"{live_server.url}/form/?auto_id=id.%s:x")
    widget = Widget(page, "attachment", element_id="id.attachment:x")
    widget.drop("notes.txt", "hello")
    widget.wait.until(lambda _: widget.file_name == "notes.txt")


def test_error_keeps_the_previous_upload(page):
    widget = Widget(page, "attachment")
    widget.drop("notes.txt", "hello")
    widget.wait.until(lambda _: widget.file_name)
    widget.drop("notes.exe", "hello")
    widget.wait.until(lambda _: widget.error.text)
    assert widget.file_name == "notes.txt"


def test_new_upload_clears_the_error(page):
    widget = Widget(page, "attachment")
    widget.drop("notes.exe", "hello")
    widget.wait.until(lambda _: widget.error.text)
    widget.drop("notes.txt", "hello")
    widget.wait.until(lambda _: widget.file_name)
    assert widget.error.text == ""


def test_failed_request(page, settings):
    widget = Widget(page, "attachment")
    page.execute_script(
        "arguments[0].setAttribute('hx-vals', JSON.stringify({'heggra-config': 'bad'}));"
        "htmx.process(arguments[0]);",
        widget.input,
    )
    widget.drop("notes.txt", "hello")
    widget.wait.until(lambda _: widget.error.text)
    assert widget.error.text == "The upload failed. Please try again."


def test_login_required(page, settings):
    settings.HEGGRA_LOGIN_REQUIRED = True
    widget = Widget(page, "attachment")
    widget.drop("notes.txt", "hello")
    widget.wait.until(lambda _: widget.error.text)
    assert widget.error.text == "Log in to upload files."


def test_image_preview(page, tmp_path):
    widget = Widget(page, "cover")
    widget.pick(write(tmp_path, "cover.png", png().read()))
    preview = widget.slot.find_element(By.CSS_SELECTOR, "img.heggra-preview")
    widget.wait.until(lambda _: page.execute_script("return arguments[0].naturalWidth", preview))
    assert "image" in preview.get_attribute("class")


def test_remove(page):
    widget = Widget(page, "attachment")
    widget.drop("notes.txt", "hello")
    widget.wait.until(lambda _: widget.file_name)
    widget.root.find_element(By.CSS_SELECTOR, "[data-heggra-remove]").click()
    assert widget.file_name is None
    assert page.switch_to.active_element == widget.input
    assert events(page)[-1] == {"type": "remove", "name": "notes.txt"}


def test_submit_keeps_the_upload_through_errors(page, tmp_path):
    widget = Widget(page, "cover")
    widget.pick(write(tmp_path, "cover.png", png().read()))
    page.find_element(By.ID, "submit").click()
    widget.wait.until(lambda _: page.find_elements(By.CSS_SELECTOR, ".errorlist"))
    widget = Widget(page, "cover")
    assert widget.file_name == "cover.png"
    page.find_element(By.ID, "id_title").send_keys("A")
    page.find_element(By.ID, "submit").click()
    widget.wait.until(lambda _: "saved" in page.find_element(By.TAG_NAME, "body").text)
    assert page.find_element(By.TAG_NAME, "body").text == "saved covers/cover.png"


def test_file_sent_with_the_form(page, tmp_path):
    # Without the script, the file goes up with the form like any file input.
    page.execute_script(
        "document.querySelectorAll('[hx-post]').forEach(e => e.removeAttribute('hx-post'))"
    )
    page.execute_script("htmx.process(document.body)")
    widget = Widget(page, "attachment")
    page.execute_script("arguments[0].removeAttribute('hx-trigger')", widget.input)
    widget.input.send_keys(str(write(tmp_path, "notes.txt", b"hello")))
    page.find_element(By.ID, "id_title").send_keys("A")
    page.find_element(By.ID, "submit").click()
    widget.wait.until(lambda _: "saved" in page.find_element(By.TAG_NAME, "body").text)
    assert page.find_element(By.TAG_NAME, "body").text == "saved attachments/notes.txt"
