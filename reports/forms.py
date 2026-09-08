from django import forms

from core.models import Unit


class PeriodReportForm(forms.Form):
    period_start = forms.DateField(widget=forms.DateInput(attrs={"class": "input", "type": "date"}))
    period_end = forms.DateField(widget=forms.DateInput(attrs={"class": "input", "type": "date"}))
    unit = forms.ModelChoiceField(
        queryset=Unit.objects.none(),
        required=False,
        widget=forms.Select(attrs={"class": "input"}),
        label="Unidade (opcional)",
        empty_label="Todas as unidades",
    )

    def __init__(self, *args, organization=None, **kwargs):
        super().__init__(*args, **kwargs)
        if organization is not None:
            self.fields["unit"].queryset = Unit.objects.filter(organization=organization)

    def clean(self):
        cleaned_data = super().clean()
        start = cleaned_data.get("period_start")
        end = cleaned_data.get("period_end")
        if start and end and start > end:
            raise forms.ValidationError("A data inicial precisa ser anterior à data final.")
        return cleaned_data
