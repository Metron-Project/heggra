from django import forms

from heggra import UploadWidget

from .models import Document


class DocumentForm(forms.ModelForm):
    class Meta:
        model = Document
        fields = ["title", "attachment", "cover"]
        widgets = {
            "attachment": UploadWidget(max_size=1024, accept=["txt", ".PDF"]),
            "cover": UploadWidget(image=True, classes={"preview": "image"}),
        }
