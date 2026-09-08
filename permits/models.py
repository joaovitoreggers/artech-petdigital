import hashlib

from django.conf import settings
from django.db import models
from django.utils import timezone

from core.models import Organization, RiskArea, Unit

from .constants import GAS_LIMITS, INTERVENTION_TYPES


class PermitSequenceCounter(models.Model):
    """Backs permits.services.generate_permit_number.

    A dedicated counter, not derived from WorkPermit's row count: counting
    existing rows breaks the moment any permit is deleted (a gap in the
    middle undercounts, so `count + 1` can collide with a number that's
    still in use higher up the sequence). This only ever increments. Kept
    per organization so every company's numbering starts at 0001.
    """

    organization = models.ForeignKey(Organization, on_delete=models.CASCADE)
    year = models.PositiveIntegerField()
    last_number = models.PositiveIntegerField(default=0)

    class Meta:
        unique_together = ("organization", "year")

    def __str__(self):
        return f"{self.organization} · {self.year} · {self.last_number}"


class WorkPermit(models.Model):
    """A Permissão de Entrada e Trabalho (PET) — the central record.

    The status machine is driven from permits.services, not from model
    methods, to keep the notification/logging side effects in one place:
    DRAFT -> (submit) -> OPEN or PENDING_APPROVAL -> (approve) -> OPEN
    OPEN -> (close) -> CLOSED, or -> INCIDENT if something went wrong.
    """

    class Status(models.TextChoices):
        DRAFT = "draft", "Rascunho"
        PENDING_APPROVAL = "pending_approval", "Aguardando aprovação"
        OPEN = "open", "Aberta"
        CLOSED = "closed", "Encerrada"
        INCIDENT = "incident", "Ocorrência"
        REJECTED = "rejected", "Rejeitada"

    INTERVENTION_TYPE_CHOICES = [(value, value) for value in INTERVENTION_TYPES]

    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name="permits")
    permit_number = models.CharField(max_length=20, editable=False)
    unit = models.ForeignKey(Unit, on_delete=models.PROTECT, related_name="permits")
    requested_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="requested_permits"
    )
    risk_areas = models.ManyToManyField(RiskArea, related_name="permits")

    description = models.TextField("descrição do serviço", blank=True)
    intervention_type = models.CharField(
        "tipo de intervenção", max_length=50, choices=INTERVENTION_TYPE_CHOICES, blank=True
    )
    contractor_company = models.CharField("empresa executante", max_length=150, blank=True)
    specific_location = models.CharField("local específico", max_length=200, blank=True)
    planned_start = models.DateTimeField("início previsto", null=True, blank=True)
    planned_end = models.DateTimeField("término previsto", null=True, blank=True)

    latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    location_accuracy_meters = models.FloatField(null=True, blank=True)
    location_fixed_at = models.DateTimeField(null=True, blank=True)

    status = models.CharField(max_length=20, choices=Status.choices, default=Status.DRAFT)

    forced_ventilation_on = models.BooleanField(default=False)
    forced_ventilation_started_at = models.DateTimeField(null=True, blank=True)

    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="approved_permits",
    )
    approved_at = models.DateTimeField(null=True, blank=True)
    rejection_reason = models.TextField(blank=True)

    opened_at = models.DateTimeField(null=True, blank=True)
    closed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        unique_together = ("organization", "permit_number")
        verbose_name = "PET"
        verbose_name_plural = "PETs"

    def __str__(self):
        return self.permit_number

    @property
    def requires_gas_monitoring(self):
        return self.risk_areas.exclude(required_gas_measurements=[]).exists()

    @property
    def required_gas_measurement_keys(self):
        """Union of gas measurement keys across the permit's selected risk
        areas, in GAS_LIMITS order — what the gas step actually asks for."""
        from .constants import GAS_LIMITS

        selected = set()
        for risk_area in self.risk_areas.all():
            selected.update(risk_area.required_gas_measurements)
        return [key for key in GAS_LIMITS if key in selected]

    @property
    def latest_gas_reading(self):
        return self.gas_readings.order_by("-recorded_at").first()

    @property
    def is_in_atmospheric_alarm(self):
        reading = self.latest_gas_reading
        return bool(reading and not reading.is_within_limits)

    @property
    def is_active(self):
        return self.status in (self.Status.OPEN, self.Status.PENDING_APPROVAL)

    @property
    def latest_ppe_verification(self):
        return self.ppe_verifications.first()  # default ordering is -submitted_at

    @property
    def ppe_verified(self):
        latest = self.latest_ppe_verification
        return bool(latest and latest.passed)


class PermitFieldValue(models.Model):
    """A per-risk-area extra field captured on the activity step.

    Generated from constants.RISK_AREA_EXTRA_FIELDS when the technician
    picks the permit's risk areas; snapshotted here so the record doesn't
    move if the field spec changes later.
    """

    work_permit = models.ForeignKey(WorkPermit, on_delete=models.CASCADE, related_name="field_values")
    risk_area = models.ForeignKey(RiskArea, on_delete=models.PROTECT)
    field_key = models.CharField(max_length=50)
    label = models.CharField(max_length=150)
    value = models.CharField(max_length=255, blank=True)

    class Meta:
        unique_together = ("work_permit", "risk_area", "field_key")

    def __str__(self):
        return f"{self.work_permit} · {self.label}"


class ChecklistItemTemplate(models.Model):
    """Seeded checklist wording (constants.RISK_AREA_CHECKLISTS).

    `risk_area` is nullable to allow a future permit-wide item that isn't
    tied to one hazard; every current template is scoped to an area.
    `regulatory_code` is the NR the *question itself* maps to, which is
    occasionally not the same as the area it's grouped under on the paper
    form (e.g. an excavation question inside the confined-space section
    that actually references NR-18 training). PPE is verified by photo,
    not by checklist question — see MandatoryPPEItem.
    """

    organization = models.ForeignKey(
        Organization, on_delete=models.CASCADE, related_name="checklist_templates"
    )
    risk_area = models.ForeignKey(
        RiskArea, on_delete=models.CASCADE, related_name="checklist_templates", null=True, blank=True
    )
    group_title = models.CharField(max_length=100)
    description = models.CharField(max_length=300)
    regulatory_code = models.CharField(max_length=10, blank=True)
    order = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ["order"]

    def __str__(self):
        return self.description


class MandatoryPPEItem(models.Model):
    """A PPE item required for a risk area (constants.RISK_AREA_MANDATORY_PPE).

    Not a checklist question: the executing worker proves these are being
    worn with one photo (PermitPPEVerification), checked against this list
    by permits.ppe_verification.
    """

    organization = models.ForeignKey(
        Organization, on_delete=models.CASCADE, related_name="mandatory_ppe_items"
    )
    risk_area = models.ForeignKey(RiskArea, on_delete=models.CASCADE, related_name="mandatory_ppe_items")
    description = models.CharField(max_length=150)
    order = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ["risk_area", "order"]
        verbose_name = "EPI obrigatório"
        verbose_name_plural = "EPIs obrigatórios"

    def __str__(self):
        return f"{self.risk_area} · {self.description}"


class PermitChecklistItem(models.Model):
    """A checklist line copied onto a specific permit at creation time.

    The wording is snapshotted (not a FK to the template) so a PET stays an
    accurate historical record even if the template text changes later.
    Matches the paper PET form: each question is answered Sim/Não/N.A.,
    not just checked off.
    """

    class Answer(models.TextChoices):
        YES = "yes", "Sim"
        NO = "no", "Não"
        NOT_APPLICABLE = "na", "N/A"

    work_permit = models.ForeignKey(WorkPermit, on_delete=models.CASCADE, related_name="checklist_items")
    group_title = models.CharField(max_length=100)
    description = models.CharField(max_length=300)
    regulatory_code = models.CharField(max_length=10, blank=True)
    answer = models.CharField(max_length=10, choices=Answer.choices, blank=True)
    answered_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["id"]

    def __str__(self):
        return self.description

    @property
    def is_answered(self):
        return bool(self.answer)

    @property
    def blocks_emission(self):
        return self.answer == self.Answer.NO

    def set_answer(self, answer):
        self.answer = answer
        self.answered_at = timezone.now() if answer else None
        self.save(update_fields=["answer", "answered_at"])


class GasReading(models.Model):
    """One manual atmospheric measurement against the NR-33 limits.

    Only the measurements the permit's risk areas actually require are
    filled in (see WorkPermit.required_gas_measurement_keys) — a
    "trabalho a quente"-only permit, for instance, never gets O₂/CO/H₂S
    values. `is_within_limits` only judges the fields that were filled.
    """

    work_permit = models.ForeignKey(WorkPermit, on_delete=models.CASCADE, related_name="gas_readings")
    oxygen = models.DecimalField("O₂ (%)", max_digits=4, decimal_places=1, null=True, blank=True)
    carbon_monoxide = models.DecimalField("CO (ppm)", max_digits=5, decimal_places=1, null=True, blank=True)
    hydrogen_sulfide = models.DecimalField("H₂S (ppm)", max_digits=4, decimal_places=1, null=True, blank=True)
    lower_explosive_limit = models.DecimalField(
        "LEL (%)", max_digits=4, decimal_places=1, null=True, blank=True
    )
    recorded_at = models.DateTimeField(auto_now_add=True)
    recorded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name="gas_readings"
    )
    is_within_limits = models.BooleanField(editable=False, default=True)

    class Meta:
        ordering = ["-recorded_at"]

    def __str__(self):
        return f"{self.work_permit} · {self.recorded_at:%d/%m %H:%M}"

    def save(self, *args, **kwargs):
        self.is_within_limits = self._compute_within_limits()
        super().save(*args, **kwargs)

    def _compute_within_limits(self):
        oxygen_limits = GAS_LIMITS["oxygen"]
        if self.oxygen is not None and not (oxygen_limits["min"] <= self.oxygen <= oxygen_limits["max"]):
            return False
        if self.carbon_monoxide is not None and self.carbon_monoxide > GAS_LIMITS["carbon_monoxide"]["max"]:
            return False
        if self.hydrogen_sulfide is not None and self.hydrogen_sulfide > GAS_LIMITS["hydrogen_sulfide"]["max"]:
            return False
        if (
            self.lower_explosive_limit is not None
            and self.lower_explosive_limit > GAS_LIMITS["lower_explosive_limit"]["max"]
        ):
            return False
        return True


class PermitTeamMember(models.Model):
    """A worker authorized (via badge scan) to execute a given permit."""

    work_permit = models.ForeignKey(WorkPermit, on_delete=models.CASCADE, related_name="team_members")
    worker = models.ForeignKey("workers.Worker", on_delete=models.PROTECT)
    added_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("work_permit", "worker")

    def __str__(self):
        return f"{self.work_permit} · {self.worker}"


class PermitPPEVerification(models.Model):
    """One attempt to prove the executing worker's PPE via photo.

    Every attempt is kept (not just the latest) for the audit trail;
    permits.services checks the most recent one to decide whether the
    wizard's "Verificação de EPI" step can advance. `items_result` is the
    AI's per-item breakdown: [{"description": ..., "present": bool}, ...].
    """

    work_permit = models.ForeignKey(WorkPermit, on_delete=models.CASCADE, related_name="ppe_verifications")
    worker = models.ForeignKey("workers.Worker", on_delete=models.SET_NULL, null=True, blank=True)
    photo = models.ImageField(upload_to="ppe_verifications/%Y/%m/")
    submitted_at = models.DateTimeField(auto_now_add=True)
    passed = models.BooleanField(default=False)
    items_result = models.JSONField(default=list, blank=True)
    ai_summary = models.CharField(max_length=500, blank=True)
    error_message = models.CharField(max_length=300, blank=True)

    class Meta:
        ordering = ["-submitted_at"]

    def __str__(self):
        return f"{self.work_permit} · {'aprovado' if self.passed else 'reprovado'} · {self.submitted_at:%d/%m %H:%M}"

    @property
    def missing_items(self):
        return [item["description"] for item in self.items_result if not item.get("present")]


class PermitSignature(models.Model):
    """A captured technician/executor signature with integrity hash + GPS."""

    class Role(models.TextChoices):
        TECHNICIAN = "technician", "Técnico de segurança emitente"
        EXECUTOR = "executor", "Executante responsável"

    work_permit = models.ForeignKey(WorkPermit, on_delete=models.CASCADE, related_name="signatures")
    role = models.CharField(max_length=20, choices=Role.choices)
    worker = models.ForeignKey("workers.Worker", on_delete=models.SET_NULL, null=True, blank=True)
    full_name = models.CharField(max_length=150)
    registration_number = models.CharField(max_length=20, blank=True)
    signature_image = models.ImageField(upload_to="signatures/%Y/%m/")
    signed_at = models.DateTimeField(auto_now_add=True)
    latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    integrity_hash = models.CharField(max_length=64, editable=False)

    class Meta:
        unique_together = ("work_permit", "role")

    def __str__(self):
        return f"{self.work_permit} · {self.get_role_display()}"

    def compute_integrity_hash(self):
        digest = hashlib.sha256()
        digest.update(self.work_permit.permit_number.encode())
        digest.update(self.full_name.encode())
        digest.update(self.registration_number.encode())
        digest.update(str(self.signed_at or timezone.now()).encode())
        self.signature_image.seek(0)
        digest.update(self.signature_image.read())
        self.signature_image.seek(0)
        return digest.hexdigest()


class PermitPhoto(models.Model):
    """A field photo attached to the checklist step (entry point, work area, ...).
    PPE photos are a separate record — see PermitPPEVerification."""

    work_permit = models.ForeignKey(WorkPermit, on_delete=models.CASCADE, related_name="photos")
    image = models.ImageField(upload_to="permit_photos/%Y/%m/")
    caption = models.CharField(max_length=150, blank=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)


class PermitLogEntry(models.Model):
    """Audit trail entry, powering both the detail screen's timeline and
    compliance record-keeping."""

    work_permit = models.ForeignKey(WorkPermit, on_delete=models.CASCADE, related_name="log_entries")
    occurred_at = models.DateTimeField(auto_now_add=True)
    event_type = models.CharField(max_length=50)
    description = models.CharField(max_length=300)
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True
    )

    class Meta:
        ordering = ["occurred_at"]
        verbose_name_plural = "log entries"

    def __str__(self):
        return f"{self.work_permit} · {self.description}"
