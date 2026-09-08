import uuid

from django.conf import settings
from django.db import models

from core.constants import DOCUMENT_EXPIRY_WARNING_DAYS
from core.models import Organization, Unit


class DocumentType(models.Model):
    """A document/certification tracked for workers (ASO, NR-33, ...).

    Each organization has its own copy, seeded from the platform's starter
    content when the organization is created (core.onboarding) and
    editable afterwards through the admin.
    """

    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name="document_types")
    code = models.CharField(max_length=10)
    name = models.CharField(max_length=100)
    description = models.CharField(max_length=200, blank=True)

    class Meta:
        ordering = ["code"]
        unique_together = ("organization", "code")
        verbose_name = "tipo de documento"
        verbose_name_plural = "tipos de documento"

    def __str__(self):
        return self.code


class Worker(models.Model):
    """A person authorized to work on site — own staff or a contractor.

    Not every worker logs into the system (most contractors don't); `user`
    links to an `accounts.User` only for workers who also act as
    technicians in the field app.
    """

    class EmploymentType(models.TextChoices):
        OWN = "own", "Próprio"
        CONTRACTOR = "contractor", "Terceiro"

    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name="workers")
    full_name = models.CharField("nome completo", max_length=150)
    registration_number = models.CharField("matrícula", max_length=20)
    job_title = models.CharField("função", max_length=100)
    company = models.CharField("empresa", max_length=150)
    employment_type = models.CharField(
        "vínculo", max_length=20, choices=EmploymentType.choices, default=EmploymentType.OWN
    )
    unit = models.ForeignKey(Unit, on_delete=models.PROTECT, related_name="workers")
    qr_token = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="worker_profile",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["full_name"]
        unique_together = ("organization", "registration_number")
        verbose_name = "funcionário"
        verbose_name_plural = "funcionários"

    def __str__(self):
        return f"{self.full_name} (mat. {self.registration_number})"

    @property
    def overall_status(self):
        """Worst status across every document this worker has on file."""
        statuses = [doc.status for doc in self.documents.all()]
        if not statuses:
            return "missing"
        if "expired" in statuses:
            return "expired"
        if "expiring_soon" in statuses:
            return "expiring_soon"
        return "valid"

    def document_status_for(self, document_type_codes):
        """Worst-case status among the given document type codes.

        Used when validating a worker against a permit's required documents
        (e.g. a confined-space permit requires ASO + NR-33): returns
        'expired' if any required document is missing/expired, 'expiring_soon'
        if none are expired but one is close, otherwise 'valid'.
        """
        documents = {doc.document_type.code: doc for doc in self.documents.all()}
        worst = "valid"
        for code in document_type_codes:
            document = documents.get(code)
            status = document.status if document else "expired"
            if status == "expired":
                return "expired"
            if status == "expiring_soon":
                worst = "expiring_soon"
        return worst


class WorkerDocument(models.Model):
    """One worker's validity record for one document type."""

    worker = models.ForeignKey(Worker, on_delete=models.CASCADE, related_name="documents")
    document_type = models.ForeignKey(DocumentType, on_delete=models.PROTECT)
    valid_until = models.DateField("validade")

    class Meta:
        unique_together = ("worker", "document_type")
        ordering = ["valid_until"]
        verbose_name = "documento do funcionário"
        verbose_name_plural = "documentos dos funcionários"

    def __str__(self):
        return f"{self.worker} · {self.document_type.code}"

    @property
    def days_remaining(self):
        from django.utils import timezone

        return (self.valid_until - timezone.localdate()).days

    @property
    def status(self):
        """'valid' / 'expiring_soon' / 'expired', matching the prototype's ok/prox/venc."""
        remaining = self.days_remaining
        if remaining < 0:
            return "expired"
        if remaining <= DOCUMENT_EXPIRY_WARNING_DAYS:
            return "expiring_soon"
        return "valid"
