"""Forms that use heggra's widget."""

from django import forms

from heggra import UploadWidget

from .models import Issue


class IssueForm(forms.ModelForm):
    """Edit an issue, uploading its cover and script as soon as they're picked or dropped."""

    class Meta:
        model = Issue
        fields = ["series", "number", "cover", "script"]
        widgets = {
            "series": forms.TextInput(attrs={"class": "input"}),
            "number": forms.TextInput(attrs={"class": "input"}),
            # A required ImageField: Pillow checks the file, and the widget shows a preview.
            "cover": UploadWidget(image=True, max_size=5 * 1024 * 1024),
            # An optional FileField limited to some extensions, which gets a clear checkbox
            # once it has a file.
            "script": UploadWidget(max_size=1024 * 1024, accept=["pdf", "txt", "md"]),
        }
        help_texts = {
            "cover": "An image of up to 5 MB.",
            "script": "A PDF, text or Markdown file of up to 1 MB.",
        }
