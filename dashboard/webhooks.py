"""Notifies registered physical-alert gateways (PhysicalAlertEndpoint) by
webhook whenever an EvacuationEvent triggers, is silenced, or ends — the
"base pronta" for driving real sirens/beacons. Delivery runs in a
background thread (this project has no task queue) so a slow or
unreachable gateway never delays the in-app alarm, which is what actually
matters in an emergency.
"""

import hashlib
import hmac
import json
import logging
import threading

import requests
from django.db.models import Q
from django.utils import timezone

logger = logging.getLogger(__name__)

REQUEST_TIMEOUT_SECONDS = 5


def _sign(secret, body):
    return hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()


def _build_payload(event, event_type):
    return {
        "event": event_type,  # "triggered" / "silenced" / "ended"
        "evacuation_id": event.pk,
        "organization": event.organization.slug,
        "unit": event.unit.name,
        "source": event.source,
        "reason": event.reason,
        "triggered_at": event.triggered_at.isoformat(),
        "siren_silenced_at": event.siren_silenced_at.isoformat() if event.siren_silenced_at else None,
        "ended_at": event.ended_at.isoformat() if event.ended_at else None,
    }


def _deliver(endpoint, body):
    headers = {"Content-Type": "application/json"}
    if endpoint.secret_token:
        headers["X-PET-Digital-Signature"] = _sign(endpoint.secret_token, body)
    try:
        response = requests.post(
            endpoint.webhook_url, data=body, headers=headers, timeout=REQUEST_TIMEOUT_SECONDS
        )
        response.raise_for_status()
        endpoint.last_delivery_status = "ok"
        endpoint.last_delivery_error = ""
    except requests.RequestException as exc:
        endpoint.last_delivery_status = "error"
        endpoint.last_delivery_error = str(exc)[:300]
        logger.warning("Falha ao notificar endpoint físico %s: %s", endpoint.webhook_url, exc)
    endpoint.last_triggered_at = timezone.now()
    endpoint.save(update_fields=["last_delivery_status", "last_delivery_error", "last_triggered_at"])


def _notify_sync(event, event_type):
    from .models import PhysicalAlertEndpoint

    endpoints = PhysicalAlertEndpoint.objects.filter(
        organization=event.organization, is_active=True
    ).filter(Q(unit__isnull=True) | Q(unit=event.unit))
    if not endpoints.exists():
        return

    body = json.dumps(_build_payload(event, event_type)).encode()
    for endpoint in endpoints:
        _deliver(endpoint, body)


def notify_physical_endpoints(event, event_type):
    """Fire-and-forget: schedules delivery on a background thread and
    returns immediately."""
    threading.Thread(target=_notify_sync, args=(event, event_type), daemon=True).start()
