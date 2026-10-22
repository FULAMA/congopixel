from django import forms
from django.contrib.auth import password_validation
from django.contrib.auth.forms import AuthenticationForm
from django.core.cache import cache
from django.core.exceptions import ValidationError

from core.validators import normalize_phone

from .models import User

MAX_LOGIN_ATTEMPTS = 5
LOCK_SECONDS = 15 * 60


class PhoneLoginForm(AuthenticationForm):
    username = forms.CharField(
        label="Téléphone", max_length=20,
        widget=forms.TextInput(attrs={"type": "tel", "inputmode": "tel", "autocomplete": "tel", "autofocus": True}),
    )

    def clean_username(self):
        return normalize_phone(self.cleaned_data["username"])

    def clean(self):
        phone = self.cleaned_data.get("username")
        key = f"login_fail:{phone}"
        if phone and cache.get(key, 0) >= MAX_LOGIN_ATTEMPTS:
            raise ValidationError("Trop de tentatives. Réessayez dans 15 minutes.", code="throttled")
        try:
            cleaned = super().clean()
        except ValidationError:
            if phone:
                cache.set(key, cache.get(key, 0) + 1, LOCK_SECONDS)
            raise
        if phone:
            cache.delete(key)
        return cleaned


class RegisterForm(forms.ModelForm):
    phone = forms.CharField(
        label="Téléphone", max_length=20,
        widget=forms.TextInput(attrs={"type": "tel", "inputmode": "tel", "autocomplete": "tel"}),
    )
    password1 = forms.CharField(label="Mot de passe", strip=False, widget=forms.PasswordInput(attrs={"autocomplete": "new-password"}))
    password2 = forms.CharField(label="Confirmez le mot de passe", strip=False, widget=forms.PasswordInput(attrs={"autocomplete": "new-password"}))

    class Meta:
        model = User
        fields = ["first_name", "last_name", "email"]
        labels = {"first_name": "Prénom", "last_name": "Nom", "email": "E-mail (facultatif)"}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["first_name"].required = True
        self.fields["last_name"].required = True

    def clean_phone(self):
        phone = normalize_phone(self.cleaned_data["phone"])
        if User.objects.filter(phone=phone).exists() or User.objects.filter(username=phone).exists():
            raise ValidationError("Un compte existe déjà avec ce numéro. Connectez-vous.")
        return phone

    def clean(self):
        cleaned = super().clean()
        p1, p2 = cleaned.get("password1"), cleaned.get("password2")
        if p1 and p2:
            if p1 != p2:
                self.add_error("password2", "Les deux mots de passe ne correspondent pas.")
            else:
                try:
                    password_validation.validate_password(p1, self.instance)
                except ValidationError as exc:
                    self.add_error("password1", exc)
        return cleaned

    def save(self, commit=True):
        user = super().save(commit=False)
        user.username = self.cleaned_data["phone"]
        user.phone = self.cleaned_data["phone"]
        user.set_password(self.cleaned_data["password1"])
        if commit:
            user.save()
        return user