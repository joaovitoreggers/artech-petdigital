from django import forms

from .models import Organization

_input = {"class": "input"}


class OrganizationOnboardingForm(forms.Form):
    name = forms.CharField(label="Nome da empresa", widget=forms.TextInput(attrs=_input))
    cnpj = forms.CharField(label="CNPJ", required=False, widget=forms.TextInput(attrs=_input))
    unit_name = forms.CharField(label="Nome da primeira unidade", widget=forms.TextInput(attrs=_input))
    unit_city = forms.CharField(label="Cidade", required=False, widget=forms.TextInput(attrs=_input))
    unit_state = forms.CharField(
        label="UF", required=False, max_length=2, widget=forms.TextInput(attrs=_input)
    )
    admin_full_name = forms.CharField(
        label="Nome completo do primeiro administrador", widget=forms.TextInput(attrs=_input)
    )
    admin_registration_number = forms.CharField(
        label="Matrícula do administrador", required=False, widget=forms.TextInput(attrs=_input)
    )

    def clean_name(self):
        name = self.cleaned_data["name"]
        if Organization.objects.filter(name__iexact=name).exists():
            raise forms.ValidationError("Já existe uma empresa cadastrada com esse nome.")
        return name
