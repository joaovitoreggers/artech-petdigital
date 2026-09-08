"""Business logic for the permit lifecycle, kept out of models/views so the
status machine and its side effects (numbering, logging) live in one place.
"""

from django.db import transaction
from django.db.models import Q
from django.utils import timezone

from .constants import BASE_REQUIRED_DOCUMENTS, RISK_AREA_REQUIRED_DOCUMENTS
from .models import (
    ChecklistItemTemplate,
    MandatoryPPEItem,
    PermitChecklistItem,
    PermitLogEntry,
    PermitSequenceCounter,
    WorkPermit,
)


def generate_permit_number(organization):
    """Atomically issue the next PET-<year>-<sequence> number for this
    organization/year — every company's numbering starts at 0001.

    Backed by PermitSequenceCounter, not WorkPermit's row count — a count
    would collide with an existing number the moment any permit in the
    middle of the sequence is deleted.
    """
    year = timezone.localdate().year
    with transaction.atomic():
        counter, _ = PermitSequenceCounter.objects.select_for_update().get_or_create(
            organization=organization, year=year
        )
        counter.last_number += 1
        counter.save(update_fields=["last_number"])
        return f"PET-{year}-{counter.last_number:04d}"


def log_event(work_permit, event_type, description, actor=None):
    return PermitLogEntry.objects.create(
        work_permit=work_permit, event_type=event_type, description=description, actor=actor
    )


def seed_checklist_items(work_permit):
    """Copy the checklist templates for the permit's selected risk areas
    onto it. PPE is verified by photo, not by checklist question — see
    required_ppe_items and permits.ppe_verification."""
    templates = ChecklistItemTemplate.objects.filter(
        Q(organization=work_permit.organization),
        Q(risk_area__isnull=True) | Q(risk_area__in=work_permit.risk_areas.all()),
    ).order_by("order")
    PermitChecklistItem.objects.bulk_create(
        [
            PermitChecklistItem(
                work_permit=work_permit,
                group_title=template.group_title,
                description=template.description,
                regulatory_code=template.regulatory_code,
            )
            for template in templates
        ]
    )


def required_document_codes(risk_areas):
    """Document type codes a worker must hold to join a permit with these areas."""
    codes = set(BASE_REQUIRED_DOCUMENTS)
    for risk_area in risk_areas:
        codes.update(RISK_AREA_REQUIRED_DOCUMENTS.get(risk_area.slug, []))
    return codes


def required_ppe_items(risk_areas):
    """Deduplicated, order-preserving list of PPE descriptions required
    across a permit's selected risk areas — what the PPE-photo step checks
    the field photo against."""
    seen = []
    for item in MandatoryPPEItem.objects.filter(risk_area__in=risk_areas).order_by("risk_area__order", "order"):
        if item.description not in seen:
            seen.append(item.description)
    return seen


def submit_permit(work_permit, technician):
    """Move a fully-filled-in DRAFT permit to OPEN or PENDING_APPROVAL.

    Technicians with `can_self_authorize` skip the approval gate entirely,
    matching the prototype's field-emission flow; everyone else waits for a
    manager (permits.services.approve_permit).
    """
    now = timezone.now()
    if technician.can_self_authorize:
        work_permit.status = WorkPermit.Status.OPEN
        work_permit.opened_at = now
        work_permit.save(update_fields=["status", "opened_at"])
        log_event(work_permit, "issued", "PET emitida — emissão autônoma em campo", actor=technician)
    else:
        work_permit.status = WorkPermit.Status.PENDING_APPROVAL
        work_permit.save(update_fields=["status"])
        log_event(work_permit, "pending_approval", "PET aguardando aprovação de um gestor", actor=technician)
    return work_permit


def approve_permit(work_permit, manager):
    now = timezone.now()
    work_permit.status = WorkPermit.Status.OPEN
    work_permit.approved_by = manager
    work_permit.approved_at = now
    work_permit.opened_at = now
    work_permit.save(update_fields=["status", "approved_by", "approved_at", "opened_at"])
    log_event(work_permit, "approved", f"PET aprovada e aberta por {manager}", actor=manager)
    return work_permit


def reject_permit(work_permit, manager, reason):
    work_permit.status = WorkPermit.Status.REJECTED
    work_permit.rejection_reason = reason
    work_permit.save(update_fields=["status", "rejection_reason"])
    log_event(work_permit, "rejected", f"PET rejeitada por {manager}: {reason}", actor=manager)
    return work_permit


def close_permit(work_permit, actor=None):
    work_permit.status = WorkPermit.Status.CLOSED
    work_permit.closed_at = timezone.now()
    work_permit.save(update_fields=["status", "closed_at"])
    log_event(work_permit, "closed", "PET encerrada", actor=actor)
    return work_permit


def flag_incident(work_permit, description, actor=None):
    work_permit.status = WorkPermit.Status.INCIDENT
    work_permit.closed_at = timezone.now()
    work_permit.save(update_fields=["status", "closed_at"])
    log_event(work_permit, "incident", description, actor=actor)
    return work_permit
