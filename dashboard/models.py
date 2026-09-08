from django.conf import settings
from django.db import models

from core.models import Organization, Unit


class EvacuationEvent(models.Model):
    """A plant-wide alarm for a unit — triggered either automatically from
    an atmospheric alarm on an open permit, or manually via the standalone
    'botão de alerta' (any technician or manager, not tied to a permit).

    Every open session polls dashboard.views.ActiveAlertStatusView for the
    active event on its own unit (see static/core/js/alert-poll.js) so the
    alarm reaches every phone with the system open — the web equivalent of
    the push notification a future native app would use instead. Trigger,
    silence and end all also fire dashboard.webhooks.notify_physical_endpoints
    in the background, for physical sirens/beacons registered on
    PhysicalAlertEndpoint.
    """

    class Source(models.TextChoices):
        GAS_ALARM = "gas_alarm", "Alarme atmosférico automático"
        MANUAL = "manual", "Alarme manual"

    organization = models.ForeignKey(
        Organization, on_delete=models.CASCADE, related_name="evacuation_events"
    )
    unit = models.ForeignKey(Unit, on_delete=models.PROTECT, related_name="evacuation_events")
    reason = models.CharField(max_length=255)
    source = models.CharField(max_length=20, choices=Source.choices, default=Source.MANUAL)
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


class PhysicalAlertEndpoint(models.Model):
    """A physical alert gateway (siren/beacon controller) to notify by
    webhook whenever an EvacuationEvent triggers, is silenced or ends.

    This is the "base pronta" for physical integration: any device that
    can receive an HTTP POST — a Raspberry Pi driving a relay, a smart
    plug, a Bluetooth-siren bridge — subscribes by being registered here.
    True Bluetooth (BLE) can only be driven from a device that actually
    has a Bluetooth radio near the siren (a phone or gateway, not this
    server), so it isn't implemented here — see the Web Bluetooth extension
    point noted in static/core/js/alert-poll.js for what a future native
    app (or a browser that supports Web Bluetooth) can hook into using the
    same active-alert signal this endpoint also delivers by webhook.
    """

    organization = models.ForeignKey(
        Organization, on_delete=models.CASCADE, related_name="physical_alert_endpoints"
    )
    unit = models.ForeignKey(
        Unit,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="physical_alert_endpoints",
        help_text="Vazio = recebe alarmes de todas as unidades desta empresa",
    )
    name = models.CharField("nome do gateway", max_length=100)
    webhook_url = models.URLField("URL do webhook")
    secret_token = models.CharField(
        "token secreto",
        max_length=64,
        blank=True,
        help_text="Enviado no header X-PET-Digital-Signature (HMAC-SHA256 do corpo) para o gateway validar a origem.",
    )
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    last_triggered_at = models.DateTimeField(null=True, blank=True)
    last_delivery_status = models.CharField(max_length=10, blank=True)
    last_delivery_error = models.CharField(max_length=300, blank=True)

    class Meta:
        ordering = ["organization", "name"]
        verbose_name = "endpoint de alerta físico"
        verbose_name_plural = "endpoints de alerta físico"

    def __str__(self):
        return f"{self.name} ({self.organization})"
