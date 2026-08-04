from django import forms
from django.contrib.auth.hashers import make_password
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _

from .models import Category, Product, Registration, Review


class RegistrationForm(forms.ModelForm):
    password = forms.CharField(
        label=_("Password"),
        widget=forms.PasswordInput(
            attrs={
                "class": "form-control",
                "placeholder": _("Enter password"),
            }
        ),
    )
    confirm_password = forms.CharField(
        label=_("Confirm Password"),
        widget=forms.PasswordInput(
            attrs={
                "class": "form-control",
                "placeholder": _("Confirm password"),
            }
        ),
    )

    class Meta:
        model = Registration
        fields = [
            "fullname",
            "email",
            "mobile",
            "password",
            "address",
            "city",
            "state",
            "pincode",
            "profile_image",
        ]
        labels = {
            "fullname": _("Full Name"),
            "email": _("Email Address"),
            "mobile": _("Mobile Number"),
            "address": _("Address"),
            "city": _("City"),
            "state": _("State"),
            "pincode": _("Pincode"),
            "profile_image": _("Profile Image"),
        }
        widgets = {
            "fullname": forms.TextInput(
                attrs={"class": "form-control", "placeholder": _("Enter full name")}
            ),
            "email": forms.EmailInput(
                attrs={"class": "form-control", "placeholder": _("Enter email address")}
            ),
            "mobile": forms.TextInput(
                attrs={"class": "form-control", "placeholder": _("Enter mobile number")}
            ),
            "address": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "placeholder": _("Enter address"),
                    "rows": 3,
                }
            ),
            "city": forms.TextInput(
                attrs={"class": "form-control", "placeholder": _("Enter city")}
            ),
            "state": forms.TextInput(
                attrs={"class": "form-control", "placeholder": _("Enter state")}
            ),
            "pincode": forms.TextInput(
                attrs={"class": "form-control", "placeholder": _("Enter pincode")}
            ),
            "profile_image": forms.ClearableFileInput(attrs={"class": "form-control"}),
        }

    def clean_email(self):
        email = self.cleaned_data["email"].strip().lower()
        if Registration.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError(_("An account with this email already exists."))
        return email

    def clean_password(self):
        password = self.cleaned_data["password"]

        try:
            validate_password(password)
        except ValidationError as error:
            raise forms.ValidationError(error.messages)

        return password

    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get("password")
        confirm_password = cleaned_data.get("confirm_password")

        if password and confirm_password and password != confirm_password:
            self.add_error("confirm_password", _("Passwords do not match."))

        return cleaned_data

    def save(self, commit=True):
        registration = super().save(commit=False)
        registration.password = make_password(self.cleaned_data["password"])

        if commit:
            registration.save()

        return registration


class LoginForm(forms.Form):
    email = forms.EmailField(
        label=_("Email"),
        widget=forms.EmailInput(
            attrs={
                "class": "form-control",
                "placeholder": _("Enter email address"),
            }
        ),
    )
    password = forms.CharField(
        label=_("Password"),
        widget=forms.PasswordInput(
            attrs={
                "class": "form-control",
                "placeholder": _("Enter password"),
            }
        ),
    )


class CategoryForm(forms.ModelForm):
    class Meta:
        model = Category
        fields = ["name_en", "name_hi", "image", "description_en", "description_hi"]
        labels = {
            "name_en": _("Category Name (English)"),
            "name_hi": _("Category Name (Hindi)"),
            "image": _("Category Image"),
            "description_en": _("Description (English)"),
            "description_hi": _("Description (Hindi)"),
        }
        widgets = {
            "name_en": forms.TextInput(
                attrs={"class": "form-control", "placeholder": _("Enter category name (English)")}
            ),
            "name_hi": forms.TextInput(
                attrs={"class": "form-control", "placeholder": _("Enter category name (Hindi)")}
            ),
            "image": forms.ClearableFileInput(attrs={"class": "form-control"}),
            "description_en": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "placeholder": _("Enter category description (English)"),
                    "rows": 4,
                }
            ),
            "description_hi": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "placeholder": _("Enter category description (Hindi)"),
                    "rows": 4,
                }
            ),
        }


class ReviewForm(forms.ModelForm):
    class Meta:
        model = Review
        fields = ["rating", "review"]
        widgets = {
            "rating": forms.NumberInput(
                attrs={"class": "form-control", "min": 1, "max": 5, "step": 1}
            ),
            "review": forms.Textarea(
                attrs={"class": "form-control", "rows": 3, "placeholder": _("Write your review...")}
            ),
        }

    def clean_rating(self):
        rating = self.cleaned_data["rating"]
        if rating < 1 or rating > 5:
            raise forms.ValidationError(_("Rating must be between 1 and 5."))
        return rating


class ProductForm(forms.ModelForm):
    class Meta:
        model = Product
        fields = [
            "category",
            "product_name_en",
            "product_name_hi",
            "product_image",
            "price",
            "stock",
            "description_en",
            "description_hi",
            "seller_name",
            "is_available",
        ]
        labels = {
            "category": _("Category"),
            "product_name_en": _("Product Name (English)"),
            "product_name_hi": _("Product Name (Hindi)"),
            "product_image": _("Product Image"),
            "price": _("Price (Rs.)"),
            "stock": _("Stock Quantity"),
            "description_en": _("Description (English)"),
            "description_hi": _("Description (Hindi)"),
            "seller_name": _("Seller Name"),
            "is_available": _("Make product available for sale"),
        }
        widgets = {
            "category": forms.Select(attrs={"class": "form-select"}),
            "product_name_en": forms.TextInput(
                attrs={"class": "form-control", "placeholder": _("Enter product name (English)")}
            ),
            "product_name_hi": forms.TextInput(
                attrs={"class": "form-control", "placeholder": _("Enter product name (Hindi)")}
            ),
            "product_image": forms.ClearableFileInput(attrs={"class": "form-control"}),
            "price": forms.NumberInput(
                attrs={
                    "class": "form-control",
                    "placeholder": _("Enter price"),
                    "min": "0",
                    "step": "0.01",
                }
            ),
            "stock": forms.NumberInput(
                attrs={
                    "class": "form-control",
                    "placeholder": _("Enter stock quantity"),
                    "min": "0",
                }
            ),
            "description_en": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "placeholder": _("Enter product description (English)"),
                    "rows": 4,
                }
            ),
            "description_hi": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "placeholder": _("Enter product description (Hindi)"),
                    "rows": 4,
                }
            ),
            "seller_name": forms.TextInput(
                attrs={"class": "form-control", "placeholder": _("Enter seller name")}
            ),
            "is_available": forms.CheckboxInput(attrs={"class": "form-check-input"}),
        }
