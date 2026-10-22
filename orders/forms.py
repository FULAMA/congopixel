from django import forms

from core.validators import normalize_phone
from payments.models import Payment

from .models import DeliveryZone, Order


class ZoneChoiceField(forms.ModelChoiceField):
    def label_from_instance(self, obj):
        label = f"{obj.name} - livraison {obj.fee_usd} $"
        if obj.estimated_delay:
            label += f" ({obj.estimated_delay})"
        return label


class CheckoutForm(forms.ModelForm):
    delivery_zone = ZoneChoiceField(
        queryset=DeliveryZone.objects.filter(is_active=True),
        label="Zone de livraison", empty_label="Choisissez votre zone",
    )
    payment_method = forms.ChoiceField(
        label="Moyen de paiement", choices=Payment.Method.choices,
        widget=forms.RadioSelect, initial=Payment.Method.ORANGE_MONEY,
    )

    class Meta:
        model = Order
        fields = ["full_name", "phone", "email", "city", "address", "delivery_zone", "notes"]
        widgets = {
            "phone": forms.TextInput(attrs={"type": "tel", "inputmode": "tel", "autocomplete": "tel"}),
            "address": forms.Textarea(attrs={"rows": 3}),
            "notes": forms.Textarea(attrs={"rows": 2}),
        }

    def clean_phone(self):
        return normalize_phone(self.cleaned_data["phone"])