import re

from django import forms
from django.core.exceptions import ValidationError

from core.validators import normalize_phone

from .models import Payment


class MobileMoneyProofForm(forms.Form):
    transaction_id = forms.CharField(
        label="ID de transaction", min_length=6, max_length=30,
        help_text="Reçu par SMS après votre paiement.",
    )
    payer_phone = forms.CharField(label="Numéro avec lequel vous avez payé", max_length=20)

    def __init__(self, *args, payment, **kwargs):
        self.payment = payment
        super().__init__(*args, **kwargs)

    def clean_transaction_id(self):
        value = re.sub(r"\s+", "", self.cleaned_data["transaction_id"]).upper()
        if not re.fullmatch(r"[A-Z0-9]{6,30}", value):
            raise ValidationError("L'ID ne doit contenir que des lettres et des chiffres.")
        already_used = (
            Payment.objects.filter(method=self.payment.method, transaction_id=value)
            .exclude(pk=self.payment.pk)
            .exists()
        )
        if already_used:
            raise ValidationError("Cet ID de transaction a déjà été utilisé. Vérifiez-le ou contactez-nous.")
        return value

    def clean_payer_phone(self):
        return normalize_phone(self.cleaned_data["payer_phone"])