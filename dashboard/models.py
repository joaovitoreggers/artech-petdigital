from django.conf import settings
from django.db import models

from core.models import Organization, Unit


class EvacuationEvent(models.Model):
    """A manager-triggered evacuation for a unit, usually following an
    atmospheric alarm on one of that unit's open permits."""

    organization = models.ForeignKey(
        Organization, on_delete=models.CASCADE, related_name="evacuation_events"
    )
    unit = models.ForeignKey(Unit, on_delete=models.PROTECT, related_name="evacuation_events")
    reason = models.CharField(max_length=255)
    triggered_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="triggered_evacuations"
    )
    triggered_at = models.DateTimeField(auto_now_add=True)
    siren_silenced_at = models.DateTimeField(null=True, blank=True)
    ended_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-triggered_at"]

    def __str__(self):
        return f"Evacuação · {self.unit} · {self.triggered_at:%d/%m %H:%M}"

    @property
    def is_active(self):
        return self.ended_at is None
