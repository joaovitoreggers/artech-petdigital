from django.conf import settings
from django.db import models

from core.models import Organization, Unit


class PeriodReport(models.Model):
    """An archived PDF covering all PETs issued in a date range.

    Kept on disk (not just streamed to the browser) to satisfy the SESMT's
    minimum 5-year retention requirement for permit records.
    """

    organization = models.ForeignKey(Organization, on_delete=models.CASCADE)
    unit = models.ForeignKey(
        Unit,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        help_text="Vazio = todas as unidades desta empresa",
    )
    period_start = models.DateField()
    period_end = models.DateField()
    generated_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    generated_at = models.DateTimeField(auto_now_add=True)
    pdf_file = models.FileField(upload_to="reports/%Y/%m/")

    class Meta:
        ordering = ["-generated_at"]

    def __str__(self):
        return f"Relatório {self.period_start} a {self.period_end}"
