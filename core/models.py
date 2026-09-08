from django.db import models


class Organization(models.Model):
    """A tenant — one industrial client company on the platform.

    Everything else in the system (units, workers, permits, and each
    company's own copy of the NR reference content) hangs off this. See
    core.onboarding.provision_organization for how a new one is created.
    """

    name = models.CharField(max_length=150, unique=True)
    slug = models.SlugField(unique=True)
    cnpj = models.CharField("CNPJ", max_length=18, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["name"]
        verbose_name = "empresa"
        verbose_name_plural = "empresas"

    def __str__(self):
        return self.name


class Unit(models.Model):
    """An industrial plant/site where permits are issued."""

    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name="units")
    name = models.CharField(max_length=100)
    city = models.CharField(max_length=100, blank=True)
    state = models.CharField(max_length=2, blank=True)

    class Meta:
        ordering = ["name"]
        unique_together = ("organization", "name")
        verbose_name = "unidade"
        verbose_name_plural = "unidades"

    def __str__(self):
        return self.name


class RiskArea(models.Model):
    """A hazard category a work permit can be issued for (NR-33, NR-18, ...).

    Each organization has its own copy — seeded from the platform's
    starter content when the organization is created (see
    core.onboarding.provision_organization) and editable afterwards
    through the admin.
    """

    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name="risk_areas")
    slug = models.SlugField(max_length=30)
    name = models.CharField(max_length=100)
    regulatory_code = models.CharField("norma", max_length=10)
    description = models.CharField(max_length=200, blank=True)
    required_gas_measurements = models.JSONField(
        "medições de gás exigidas",
        default=list,
        blank=True,
        help_text=(
            "Chaves de permits.constants.GAS_LIMITS aplicáveis a esta área "
            "(oxygen, carbon_monoxide, hydrogen_sulfide, lower_explosive_limit). "
            "Vazio = a etapa de medição atmosférica não aparece para esta área."
        ),
    )
    order = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ["order", "name"]
        unique_together = ("organization", "slug")
        verbose_name = "área de risco"
        verbose_name_plural = "áreas de risco"

    def __str__(self):
        return f"{self.name} ({self.regulatory_code})"
