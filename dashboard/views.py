from datetime import timedelta

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Count, Q
from django.db.models.functions import TruncDate
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse
from django.utils import timezone
from django.views import View
from django.views.generic import TemplateView

from core.mixins import AlertTriggerRequiredMixin, ManagerRequiredMixin
from core.models import RiskArea
from permits.models import GasReading, WorkPermit

from . import webhooks
from .models import EvacuationEvent

CHART_WINDOW_DAYS = 30


def _unit_permits(user):
    """Non-draft permits for this manager's organization — narrowed further
    to their own unit when they have one, otherwise every unit in the
    organization (never another company's, even if `unit` is unset)."""
    permits = WorkPermit.objects.filter(organization=user.organization)
    if user.unit:
        permits = permits.filter(unit=user.unit)
    return permits.exclude(status=WorkPermit.Status.DRAFT)


class DashboardHomeView(ManagerRequiredMixin, TemplateView):
    template_name = "dashboard/home.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        permits = _unit_permits(user)
        window_start = timezone.now() - timedelta(days=CHART_WINDOW_DAYS)

        open_permits = list(
            permits.filter(status=WorkPermit.Status.OPEN)
            .select_related("unit")
            .prefetch_related("risk_areas", "gas_readings")
        )
        active_evacuation = EvacuationEvent.objects.filter(
            organization=user.organization, ended_at__isnull=True
        ).first()
        alarmed_permit = next((p for p in open_permits if p.is_in_atmospheric_alarm), None)

        recent_evacuations = EvacuationEvent.objects.filter(
            organization=user.organization
        ).select_related("unit", "triggered_by")
        if user.unit:
            recent_evacuations = recent_evacuations.filter(unit=user.unit)
        recent_evacuations = recent_evacuations.order_by("-triggered_at")[:10]

        context.update(
            {
                "kpis": self._kpis(permits, window_start),
                "open_permits": open_permits,
                "alarmed_permit": alarmed_permit,
                "active_evacuation": active_evacuation,
                "recent_evacuations": recent_evacuations,
                "pending_approval_count": permits.filter(
                    status=WorkPermit.Status.PENDING_APPROVAL
                ).count(),
                "chart_days": self._chart_days(permits, window_start),
                "risk_area_analysis": self._risk_area_analysis(user, permits),
                "incidents": permits.filter(status=WorkPermit.Status.INCIDENT).order_by("-closed_at")[:10],
            }
        )
        return context

    def _kpis(self, permits, window_start):
        readings = GasReading.objects.filter(work_permit__in=permits, recorded_at__gte=window_start)
        total_readings = readings.count()
        within_limits = readings.filter(is_within_limits=True).count()
        compliance = round((within_limits / total_readings) * 100, 1) if total_readings else 100.0
        return {
            "open_now": permits.filter(status=WorkPermit.Status.OPEN).count(),
            "closed_last_30_days": permits.filter(
                status=WorkPermit.Status.CLOSED, closed_at__gte=window_start
            ).count(),
            "incidents_last_30_days": permits.filter(
                status=WorkPermit.Status.INCIDENT, closed_at__gte=window_start
            ).count(),
            "atmospheric_compliance": compliance,
        }

    def _chart_days(self, permits, window_start):
        readings = (
            GasReading.objects.filter(work_permit__in=permits, recorded_at__gte=window_start)
            .annotate(day=TruncDate("recorded_at"))
            .values("day")
            .annotate(total=Count("id"), out_of_limits=Count("id", filter=Q(is_within_limits=False)))
        )
        by_day = {row["day"]: row for row in readings}
        today = timezone.localdate()
        days = []
        for offset in range(CHART_WINDOW_DAYS - 1, -1, -1):
            day = today - timedelta(days=offset)
            row = by_day.get(day, {"total": 0, "out_of_limits": 0})
            total = row["total"] or 1  # avoid div-by-zero for the bar-height ratio
            days.append(
                {
                    "date": day,
                    "total": row["total"],
                    "out_of_limits": row["out_of_limits"],
                    "height_pct": min(100, row["total"] * 4),
                    "out_pct": round((row["out_of_limits"] / total) * 100),
                }
            )
        return days

    def _risk_area_analysis(self, user, permits):
        analysis = []
        for risk_area in RiskArea.objects.filter(organization=user.organization):
            area_permits = permits.filter(risk_areas=risk_area)
            total = area_permits.count()
            incidents = area_permits.filter(status=WorkPermit.Status.INCIDENT).count()
            rate = round((incidents / total) * 100, 1) if total else 0.0
            analysis.append(
                {"risk_area": risk_area, "total": total, "incidents": incidents, "rate": rate}
            )
        return analysis


class HistoryView(ManagerRequiredMixin, TemplateView):
    template_name = "dashboard/history.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        permits = _unit_permits(user)
        risk_area_slug = self.request.GET.get("risk_area")
        if risk_area_slug:
            permits = permits.filter(risk_areas__slug=risk_area_slug)
        context["risk_areas"] = RiskArea.objects.filter(organization=user.organization)
        context["selected_risk_area"] = risk_area_slug or ""
        context["permits"] = permits.select_related("unit").prefetch_related("risk_areas").order_by(
            "-created_at"
        )[:100]

        evacuations = EvacuationEvent.objects.filter(organization=user.organization).select_related(
            "unit", "triggered_by"
        )
        if user.unit:
            evacuations = evacuations.filter(unit=user.unit)
        context["evacuations"] = evacuations.order_by("-triggered_at")[:100]
        return context


class TriggerEvacuationView(ManagerRequiredMixin, View):
    """Evacuation triggered from a specific permit's atmospheric alarm."""

    def post(self, request, pk):
        permit = get_object_or_404(WorkPermit, pk=pk, organization=request.user.organization)
        event = EvacuationEvent.objects.create(
            organization=permit.organization,
            unit=permit.unit,
            reason=f"Alerta atmosférico na {permit.permit_number}",
            source=EvacuationEvent.Source.GAS_ALARM,
            triggered_by=request.user,
        )
        webhooks.notify_physical_endpoints(event, "triggered")
        return redirect(reverse("dashboard:home"))


class TriggerGeneralAlertView(AlertTriggerRequiredMixin, View):
    """The standalone 'botão de alerta' in the top nav — not tied to any
    permit, usable by whoever notices danger first in the field."""

    def post(self, request):
        user = request.user
        if not user.unit:
            messages.error(request, "Seu usuário não tem uma unidade associada — não é possível acionar o alarme.")
            return redirect("core:home")

        reason = request.POST.get("reason", "").strip() or f"Alarme geral acionado por {user}"
        event = EvacuationEvent.objects.create(
            organization=user.organization,
            unit=user.unit,
            reason=reason,
            source=EvacuationEvent.Source.MANUAL,
            triggered_by=user,
        )
        webhooks.notify_physical_endpoints(event, "triggered")
        messages.success(request, "Alarme geral acionado.")
        return redirect(request.headers.get("referer") or reverse("core:home"))


class ActiveAlertStatusView(LoginRequiredMixin, View):
    """Polled every few seconds by every authenticated page (see
    static/core/js/alert-poll.js) so an alarm triggered anywhere reaches
    every open session — the web equivalent of the push notification a
    future native app would receive instead."""

    def get(self, request):
        user = request.user
        events = EvacuationEvent.objects.filter(organization=user.organization, ended_at__isnull=True)
        if user.unit:
            events = events.filter(unit=user.unit)
        event = events.select_related("unit", "triggered_by").order_by("-triggered_at").first()
        if not event:
            return JsonResponse({"active": False})
        return JsonResponse(
            {
                "active": True,
                "id": event.pk,
                "reason": event.reason,
                "unit": event.unit.name,
                "triggered_by": event.triggered_by.get_full_name() or event.triggered_by.username,
                "triggered_at": event.triggered_at.isoformat(),
                "triggered_at_label": timezone.localtime(event.triggered_at).strftime("%H:%M"),
                "silenced": event.siren_silenced_at is not None,
            }
        )


class SilenceSirenView(ManagerRequiredMixin, View):
    def post(self, request, pk):
        event = get_object_or_404(
            EvacuationEvent, pk=pk, organization=request.user.organization, ended_at__isnull=True
        )
        event.siren_silenced_at = timezone.now()
        event.save(update_fields=["siren_silenced_at"])
        webhooks.notify_physical_endpoints(event, "silenced")
        return redirect(reverse("dashboard:home"))


class EndEvacuationView(ManagerRequiredMixin, View):
    def post(self, request, pk):
        event = get_object_or_404(
            EvacuationEvent, pk=pk, organization=request.user.organization, ended_at__isnull=True
        )
        event.ended_at = timezone.now()
        event.save(update_fields=["ended_at"])
        webhooks.notify_physical_endpoints(event, "ended")
        return redirect(reverse("dashboard:home"))
