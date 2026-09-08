from django import forms
from django.forms import modelformset_factory

from core.models import Unit

from .models import DocumentType, Worker, WorkerDocument


class WorkerForm(forms.ModelForm):
    unit = forms.ModelChoiceField(
        queryset=Unit.objects.none(),
        empty_label="Selecione a unidade",
        widget=forms.Select(attrs={"class": "input"}),
        label="Unidade",
    )

    class Meta:
        model = Worker
        fields = ["full_name", "registration_number", "job_title", "company", "unit", "employment_type"]
        widgets = {
            "full_name": forms.TextInput(attrs={"class": "input", "placeholder": "ex. Marina T. Baldissera"}),
            "registration_number": forms.TextInput(attrs={"class": "input", "placeholder": "05xxx"}),
            "job_title": forms.TextInput(attrs={"class": "input", "placeholder": "ex. Mecânica industrial"}),
            "company": forms.TextInput(attrs={"class": "input", "placeholder": "ex. Lar · Manutenção"}),
            "unit": forms.Select(attrs={"class": "input"}),
            "employment_type": forms.Select(attrs={"class": "input"}),
        }

    def __init__(self, *args, organization=None, **kwargs):
        super().__init__(*args, **kwargs)
        if organization is not None:
            self.fields["unit"].queryset = Unit.objects.filter(organization=organization)


class WorkerDocumentForm(forms.ModelForm):
    class Meta:
        model = WorkerDocument
        fields = ["document_type", "valid_until"]
        widgets = {
            "document_type": forms.HiddenInput(),
            "valid_until": forms.DateInput(attrs={"class": "input", "type": "date"}),
        }


def build_document_formset(organization, worker=None, data=None):
    """One (possibly blank) form per known DocumentType for the worker.

    Leaving a form's date empty means that document type isn't tracked for
    this worker; the view skips saving those rows.

    `extra` is computed per call (not fixed on a module-level factory)
    because a formset only ever renders `extra` blank forms regardless of
    how much `initial` data is passed — with a fixed extra=0 no document
    rows would ever appear.
    """
    document_types = list(DocumentType.objects.filter(organization=organization))
    existing = {d.document_type_id: d for d in worker.documents.all()} if worker else {}
    initial = [
        {"document_type": document_type.pk, "valid_until": existing.get(document_type.pk) and existing[document_type.pk].valid_until}
        for document_type in document_types
    ]
    formset_class = modelformset_factory(
        WorkerDocument, form=WorkerDocumentForm, extra=len(document_types), can_delete=False
    )
    formset = formset_class(
        data=data,
        queryset=WorkerDocument.objects.none(),
        initial=initial,
        prefix="documents",
    )
    for form, document_type in zip(formset.forms, document_types):
        form.document_type_label = document_type
    return formset
