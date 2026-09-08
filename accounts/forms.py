from django import forms
from django.core.validators import RegexValidator

from .pin import PIN_LENGTH

pin_format_validator = RegexValidator(
    regex=rf"^\d{{{PIN_LENGTH}}}$", message=f"Informe os {PIN_LENGTH} dígitos do PIN."
)


class PinLoginForm(forms.Form):
    pin = forms.CharField(
        label="PIN",
        max_length=PIN_LENGTH,
        validators=[pin_format_validator],
        widget=forms.PasswordInput(
            attrs={
                "inputmode": "numeric",
                "autocomplete": "off",
                "pattern": r"\d*",
                "class": "input",
                "style": "display:none;",
            }
        ),
    )
