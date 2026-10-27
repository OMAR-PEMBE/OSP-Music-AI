import re

from django import forms
from django.contrib.auth import get_user_model

DISPLAY_NAME_RE = re.compile(r"^[A-Za-z0-9_]{3,30}$")


class OSPSignupForm(forms.Form):
    first_name = forms.CharField(max_length=60)
    last_name = forms.CharField(max_length=60)
    display_name = forms.CharField(max_length=30, min_length=3)

    def clean_first_name(self):
        return self.cleaned_data["first_name"].strip()

    def clean_last_name(self):
        return self.cleaned_data["last_name"].strip()

    def clean_display_name(self):
        display_name = self.cleaned_data["display_name"].strip()
        if not DISPLAY_NAME_RE.fullmatch(display_name):
            raise forms.ValidationError("Use 3 to 30 letters, numbers, or underscores.")
        user_model = get_user_model()
        if user_model.objects.filter(display_name__iexact=display_name).exists():
            raise forms.ValidationError("This display name is already in use.")
        return display_name

    def signup(self, request, user):
        user.first_name = self.cleaned_data["first_name"]
        user.last_name = self.cleaned_data["last_name"]
        user.display_name = self.cleaned_data["display_name"]
        user.save(update_fields=["first_name", "last_name", "display_name"])
