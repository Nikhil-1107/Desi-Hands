from django import forms
from django.contrib.auth.hashers import make_password
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError

from .models import Registration


class ProfileForm(forms.ModelForm):
    class Meta:
        model = Registration
        fields = [
            "fullname",
            "email",
            "mobile",
            "address",
            "city",
            "state",
            "pincode",
            "profile_image",
        ]
        widgets = {
            "fullname": forms.TextInput(attrs={"class": "form-control"}),
            "email": forms.EmailInput(attrs={"class": "form-control", "readonly": "readonly"}),
            "mobile": forms.TextInput(attrs={"class": "form-control"}),
            "address": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
            "city": forms.TextInput(attrs={"class": "form-control"}),
            "state": forms.TextInput(attrs={"class": "form-control"}),
            "pincode": forms.TextInput(attrs={"class": "form-control"}),
            "profile_image": forms.ClearableFileInput(attrs={"class": "form-control"}),
        }


class ChangePasswordForm(forms.Form):
    old_password = forms.CharField(
        widget=forms.PasswordInput(attrs={"class": "form-control"}),
    )
    new_password = forms.CharField(
        widget=forms.PasswordInput(attrs={"class": "form-control"}),
    )
    confirm_password = forms.CharField(
        widget=forms.PasswordInput(attrs={"class": "form-control"}),
    )

    def clean_new_password(self):
        new_password = self.cleaned_data.get("new_password")
        try:
            validate_password(new_password)
        except ValidationError as e:
            raise forms.ValidationError(e.messages)
        return new_password

    def clean(self):
        cleaned_data = super().clean()
        new_password = cleaned_data.get("new_password")
        confirm_password = cleaned_data.get("confirm_password")
        if new_password and confirm_password and new_password != confirm_password:
            self.add_error("confirm_password", "Passwords do not match.")
        return cleaned_data

