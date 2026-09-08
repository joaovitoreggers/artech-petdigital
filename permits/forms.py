from django import forms

from core.models import RiskArea

from .constants import INTERVENTION_TYPES
from .models import GasReading, WorkPermit

INTERVENTION_TYPE_CHOICES = [("", "Selecione o tipo de intervenção")] + [
    (value, value) for value in INTERVENTION_TYPES
]


class RiskAreaSelectionForm(forms.Form):
    risk_areas = forms.ModelMultipleChoiceField(
        queryset=RiskArea.objects.none(),
        widget=forms.CheckboxSelectMultiple,
        label="",
    )

    def __init__(self, *args, organization=None, **kwargs):
        super().__init__(*args, **kwargs)
        if organization is not None:
            self.fields["risk_areas"].queryset = RiskArea.objects.filter(organization=organization)


class PermitActivityForm(forms.ModelForm):
    # Declared explicitly (rather than via Meta.widgets) because Django
    # rebuilds a ModelForm choice field's widget choices from the model
    # field's own `choices`, silently discarding a widget-level override —
    # only an explicitly declared field's choices stick.
    intervention_type = forms.ChoiceField(
        choices=INTERVENTION_TYPE_CHOICES,
        required=False,
        widget=forms.Select(attrs={"class": "input"}),
        label="Tipo de intervenção",
    )
    latitude = forms.DecimalField(widget=forms.HiddenInput, required=False)
    longitude = forms.DecimalField(widget=forms.HiddenInput, required=False)
    location_accuracy_meters = forms.FloatField(widget=forms.HiddenInput, required=False)

    class Meta:
        model = WorkPermit
        fields = [
            "description",
            "intervention_type",
            "contractor_company",
            "specific_location",
            "planned_start",
            "planned_end",
        ]
        widgets = {
            "description": forms.Textarea(attrs={"class": "input", "style": "min-height:74px"}),
            "contractor_company": forms.TextInput(attrs={"class": "input"}),
            "specific_location": forms.TextInput(attrs={"class": "input"}),
            "planned_start": forms.DateTimeInput(attrs={"class": "input", "type": "datetime-local"}),
            "planned_end": forms.DateTimeInput(attrs={"class": "input", "type": "datetime-local"}),
        }

    def save(self, commit=True):
        instance = super().save(commit=False)
        latitude = self.cleaned_data.get("latitude")
        longitude = self.cleaned_data.get("longitude")
        if latitude is not None and longitude is not None:
            from django.utils import timezone

            instance.latitude = latitude
            instance.longitude = longitude
            instance.location_accuracy_meters = self.cleaned_data.get("location_accuracy_meters")
            instance.location_fixed_at = timezone.now()
        if commit:
            instance.save()
        return instance


class GasReadingForm(forms.ModelForm):
    """Only exposes the measurement fields the permit's risk areas require —
    e.g. a "trabalho a quente"-only permit never asks for O₂/CO/H₂S."""

    class Meta:
        model = GasReading
        fields = ["oxygen", "carbon_monoxide", "hydrogen_sulfide", "lower_explosive_limit"]
        widgets = {
            "oxygen": forms.NumberInput(attrs={"class": "input", "step": "0.1"}),
            "carbon_monoxide": forms.NumberInput(attrs={"class": "input", "step": "0.1"}),
            "hydrogen_sulfide": forms.NumberInput(attrs={"class": "input", "step": "0.1"}),
            "lower_explosive_limit": forms.NumberInput(attrs={"class": "input", "step": "0.1"}),
        }

    def __init__(self, *args, required_measurements=(), **kwargs):
        super().__init__(*args, **kwargs)
        for field_name in list(self.fields):
            if field_name not in required_measurements:
                del self.fields[field_name]
            else:
                self.fields[field_name].required = True
