import base64

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.files.base import ContentFile
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views import View
from django.views.generic import DetailView, TemplateView

from core.mixins import ManagerRequiredMixin, TechnicianRequiredMixin
from core.models import RiskArea
from workers.models import Worker

from . import gas_anomaly, ppe_verification, priority_score, risk_suggestion, services, wizard
from .constants import CONFINED_SPACE_GENERAL_GUIDANCE, gas_measurement_specs
from .forms import GasReadingForm, PermitActivityForm, RiskAreaSelectionForm
from .models import (
    PermitChecklistItem,
    PermitFieldValue,
    PermitPPEVerification,
    PermitSignature,
    PermitTeamMember,
    WorkPermit,
)


class PermitHomeView(TechnicianRequiredMixin, TemplateView):
    """Mobile 'home' screen: Abertas (open + pending approval) / Encerradas tabs."""

    template_name = "permits/permit_home.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["missing_unit"] = self.request.user.unit is None
        queryset = WorkPermit.objects.filter(
            organization=self.request.user.organization, unit=self.request.user.unit
        ).select_related("unit")
        tab = self.request.GET.get("tab", "open")
        open_statuses = [WorkPermit.Status.OPEN, WorkPermit.Status.PENDING_APPROVAL]
        closed_statuses = [WorkPermit.Status.CLOSED, WorkPermit.Status.INCIDENT, WorkPermit.Status.REJECTED]
        context["tab"] = tab
        context["open_count"] = queryset.filter(status__in=open_statuses).count()
        context["closed_count"] = queryset.filter(status__in=closed_statuses).count()
        statuses = open_statuses if tab == "open" else closed_statuses
        context["permits"] = queryset.filter(status__in=statuses).order_by("-created_at")
        return context


class PermitCreateView(TechnicianRequiredMixin, View):
    """Start a new draft permit and enter the wizard at its first step."""

    def post(self, request):
        if request.user.unit is None:
            messages.error(
                request,
                "Seu usuário não tem uma unidade associada. Peça a um administrador para "
                "configurar sua unidade em /admin/ antes de emitir PETs.",
            )
            return redirect("permits:home")
        work_permit = WorkPermit.objects.create(
            permit_number=services.generate_permit_number(request.user.organization),
            organization=request.user.organization,
            unit=request.user.unit,
            requested_by=request.user,
        )
        services.log_event(work_permit, "created", "Rascunho de PET iniciado em campo", actor=request.user)
        return redirect("permits:wizard_area", pk=work_permit.pk)


class DraftPermitMixin(LoginRequiredMixin):
    """Fetch the technician's own draft permit for a wizard step."""

    def dispatch(self, request, *args, **kwargs):
        self.work_permit = get_object_or_404(
            WorkPermit, pk=kwargs["pk"], requested_by=request.user, status=WorkPermit.Status.DRAFT
        )
        return super().dispatch(request, *args, **kwargs)

    def wizard_render(self, request, step_slug, template_suffix, extra_context):
        context = wizard.step_context(self.work_permit, step_slug)
        context.update(extra_context)
        context["work_permit"] = self.work_permit
        return render(request, f"permits/wizard_{template_suffix}.html", context)

    def go_next(self, step_slug):
        step = wizard.next_step(self.work_permit, step_slug)
        if step is None:
            return redirect("permits:wizard_signatures", pk=self.work_permit.pk)
        return redirect(step.url_name, pk=self.work_permit.pk)

    def go_previous(self, step_slug):
        step = wizard.previous_step(self.work_permit, step_slug)
        if step is None:
            return redirect("permits:home")
        return redirect(step.url_name, pk=self.work_permit.pk)


class WizardAreaView(DraftPermitMixin, View):
    step_slug = "area"

    def get(self, request, pk):
        form = RiskAreaSelectionForm(
            initial={"risk_areas": self.work_permit.risk_areas.all()},
            organization=self.work_permit.organization,
        )
        selected_ids = set(self.work_permit.risk_areas.values_list("id", flat=True))
        return self.wizard_render(
            request,
            self.step_slug,
            "area",
            {
                "form": form,
                "risk_areas": RiskArea.objects.filter(organization=self.work_permit.organization),
                "selected_ids": selected_ids,
            },
        )

    def post(self, request, pk):
        if "back" in request.POST:
            return redirect("permits:home")
        form = RiskAreaSelectionForm(request.POST, organization=self.work_permit.organization)
        if not form.is_valid():
            return self.wizard_render(request, self.step_slug, "area", {"form": form})

        selected = form.cleaned_data["risk_areas"]
        self.work_permit.risk_areas.set(selected)
        self._sync_extra_fields(selected)
        return self.go_next(self.step_slug)

    def _sync_extra_fields(self, selected_areas):
        from .constants import RISK_AREA_EXTRA_FIELDS

        self.work_permit.field_values.exclude(risk_area__in=selected_areas).delete()
        existing_keys = set(
            self.work_permit.field_values.values_list("risk_area__slug", "field_key")
        )
        new_rows = []
        for risk_area in selected_areas:
            for field in RISK_AREA_EXTRA_FIELDS.get(risk_area.slug, []):
                if (risk_area.slug, field["key"]) in existing_keys:
                    continue
                new_rows.append(
                    PermitFieldValue(
                        work_permit=self.work_permit,
                        risk_area=risk_area,
                        field_key=field["key"],
                        label=field["label"],
                    )
                )
        PermitFieldValue.objects.bulk_create(new_rows)


class WizardAreaSuggestView(DraftPermitMixin, View):
    """AJAX helper for the 'Área de risco' step: given a free-text
    description of the activity, returns which risk areas the AI thinks
    apply so the technician starts from pre-checked boxes instead of a
    blank list — still reviewed and confirmed before advancing."""

    def post(self, request, pk):
        description = request.POST.get("description", "").strip()
        if not description:
            return JsonResponse(
                {"success": False, "error": "Descreva a atividade antes de pedir a sugestão."}, status=400
            )
        risk_areas = RiskArea.objects.filter(organization=self.work_permit.organization)
        try:
            result = risk_suggestion.suggest_risk_areas(description, risk_areas)
        except risk_suggestion.RiskSuggestionError as exc:
            return JsonResponse({"success": False, "error": str(exc)}, status=502)
        return JsonResponse(
            {"success": True, "suggested_ids": result["suggested_ids"], "reasoning": result["reasoning"]}
        )


class WizardActivityView(DraftPermitMixin, View):
    step_slug = "activity"

    def get(self, request, pk):
        form = PermitActivityForm(instance=self.work_permit)
        extra_fields = self.work_permit.field_values.select_related("risk_area").order_by("risk_area__order")
        return self.wizard_render(
            request, self.step_slug, "activity", {"form": form, "extra_fields": extra_fields}
        )

    def post(self, request, pk):
        if "back" in request.POST:
            return self.go_previous(self.step_slug)
        form = PermitActivityForm(request.POST, instance=self.work_permit)
        extra_fields = list(
            self.work_permit.field_values.select_related("risk_area").order_by("risk_area__order")
        )
        if not form.is_valid():
            return self.wizard_render(
                request, self.step_slug, "activity", {"form": form, "extra_fields": extra_fields}
            )
        form.save()
        for field_value in extra_fields:
            field_value.value = request.POST.get(f"extra_{field_value.pk}", "")
            field_value.save(update_fields=["value"])
        return self.go_next(self.step_slug)


class WizardGasView(DraftPermitMixin, View):
    """Only asks for the gas measurements the permit's selected risk areas
    actually require (WorkPermit.required_gas_measurement_keys) — a
    "trabalho a quente"-only permit only asks for LEL, not O₂/CO/H₂S."""

    step_slug = "gas"

    def get(self, request, pk):
        required = self.work_permit.required_gas_measurement_keys
        return self._render(request, GasReadingForm(required_measurements=required), required)

    def post(self, request, pk):
        required = self.work_permit.required_gas_measurement_keys
        if "back" in request.POST:
            return self.go_previous(self.step_slug)
        if "toggle_ventilation" in request.POST:
            self.work_permit.forced_ventilation_on = not self.work_permit.forced_ventilation_on
            self.work_permit.forced_ventilation_started_at = (
                timezone.now() if self.work_permit.forced_ventilation_on else None
            )
            self.work_permit.save(update_fields=["forced_ventilation_on", "forced_ventilation_started_at"])
            return redirect("permits:wizard_gas", pk=pk)
        if "record_reading" in request.POST:
            form = GasReadingForm(request.POST, required_measurements=required)
            if form.is_valid():
                reading = form.save(commit=False)
                reading.work_permit = self.work_permit
                reading.recorded_by = request.user
                reading.save()
                for anomaly in gas_anomaly.detect_anomalies(self.work_permit, reading):
                    messages.warning(request, f"⚠ {anomaly.message}")
                return redirect("permits:wizard_gas", pk=pk)
            return self._render(request, form, required)
        if "advance" in request.POST:
            latest = self.work_permit.latest_gas_reading
            if not latest or not latest.is_within_limits:
                messages.error(
                    request,
                    "Emissão bloqueada enquanto a atmosfera estiver fora do limite. "
                    "Ligue a ventilação forçada e registre uma nova leitura antes de avançar.",
                )
                return redirect("permits:wizard_gas", pk=pk)
            return self.go_next(self.step_slug)
        return redirect("permits:wizard_gas", pk=pk)

    def _render(self, request, form, required):
        readings = self.work_permit.gas_readings.all()[:10]
        return self.wizard_render(
            request,
            self.step_slug,
            "gas",
            {
                "form": form,
                "readings": readings,
                "gauge_specs": gas_measurement_specs(required),
            },
        )


def _scanned_worker_context(mixin, scanned_worker):
    required = services.required_document_codes(mixin.work_permit.risk_areas.all())
    return {
        "work_permit": mixin.work_permit,
        "scanned_worker": scanned_worker,
        "scanned_status": scanned_worker.document_status_for(required) if scanned_worker else None,
    }


def _render_team_step(mixin, request, scanned_worker=None):
    context = _scanned_worker_context(mixin, scanned_worker)
    context["team_members"] = mixin.work_permit.team_members.select_related("worker")
    return mixin.wizard_render(request, "team", "team", context)


class WizardTeamView(DraftPermitMixin, View):
    step_slug = "team"

    def get(self, request, pk):
        return _render_team_step(self, request)

    def post(self, request, pk):
        if "back" in request.POST:
            return self.go_previous(self.step_slug)
        if "advance" in request.POST:
            if not self.work_permit.team_members.exists():
                messages.error(request, "Adicione ao menos um executante à equipe autorizada.")
                return redirect("permits:wizard_team", pk=pk)
            return self.go_next(self.step_slug)
        if "add_worker" in request.POST:
            worker = get_object_or_404(
                Worker, pk=request.POST["worker_id"], organization=self.work_permit.organization
            )
            required = services.required_document_codes(self.work_permit.risk_areas.all())
            if worker.document_status_for(required) == "expired":
                messages.error(request, f"{worker.full_name} tem documentação vencida — não pode ser adicionado.")
            else:
                PermitTeamMember.objects.get_or_create(work_permit=self.work_permit, worker=worker)
            return redirect("permits:wizard_team", pk=pk)
        return redirect("permits:wizard_team", pk=pk)


class WizardTeamScanView(DraftPermitMixin, View):
    """Fetch endpoint: the camera decoded a badge QR, look the worker up.

    Returns only the scanned-worker fragment (see _scanned_worker.html),
    swapped into the wizard page by static/permits/js/wizard.js.
    """

    def post(self, request, pk):
        token = request.POST.get("token", "").strip()
        worker = Worker.objects.filter(qr_token=token, organization=self.work_permit.organization).first()
        context = _scanned_worker_context(self, worker)
        if not worker:
            context["not_found"] = True
        return render(request, "permits/_scanned_worker.html", context)


class WizardPPEView(DraftPermitMixin, View):
    """PPE proof step: the executing worker's photo is checked against the
    permit's mandatory PPE list (permits.ppe_verification) instead of the
    old yes/no PPE checklist questions."""

    step_slug = "ppe"

    def get(self, request, pk):
        return self._render(request)

    def post(self, request, pk):
        if "back" in request.POST:
            return self.go_previous(self.step_slug)
        if "verify" in request.POST:
            return self._handle_verify(request)
        if "advance" in request.POST:
            if not self.work_permit.ppe_verified:
                messages.error(request, "Envie uma foto e aguarde a aprovação da verificação de EPI antes de avançar.")
                return redirect("permits:wizard_ppe", pk=pk)
            return self.go_next(self.step_slug)
        return redirect("permits:wizard_ppe", pk=pk)

    def _handle_verify(self, request):
        photo = request.FILES.get("photo")
        if not photo:
            messages.error(request, "Selecione ou tire uma foto para enviar.")
            return redirect("permits:wizard_ppe", pk=self.work_permit.pk)

        worker_id = request.POST.get("worker_id") or None
        worker = (
            Worker.objects.filter(pk=worker_id, organization=self.work_permit.organization).first()
            if worker_id
            else None
        )
        required_items = services.required_ppe_items(self.work_permit.risk_areas.all())
        photo_bytes = photo.read()
        photo.seek(0)

        try:
            result = ppe_verification.verify_ppe_photo(photo_bytes, required_items)
        except ppe_verification.PPEVerificationError as exc:
            PermitPPEVerification.objects.create(
                work_permit=self.work_permit, worker=worker, photo=photo, passed=False, error_message=str(exc)
            )
            messages.error(request, f"Não foi possível verificar a foto: {exc}")
            return redirect("permits:wizard_ppe", pk=self.work_permit.pk)

        verification = PermitPPEVerification.objects.create(
            work_permit=self.work_permit,
            worker=worker,
            photo=photo,
            passed=result["passed"],
            items_result=result["items_result"],
            ai_summary=result["summary"],
        )
        if verification.passed:
            messages.success(request, "EPIs verificados com sucesso — pode avançar.")
        else:
            missing = ", ".join(verification.missing_items) or "itens não identificados"
            messages.error(request, f"EPIs não identificados na foto: {missing}. Ajuste e envie outra foto.")
        return redirect("permits:wizard_ppe", pk=self.work_permit.pk)

    def _render(self, request):
        required_items = services.required_ppe_items(self.work_permit.risk_areas.all())
        return self.wizard_render(
            request,
            self.step_slug,
            "ppe",
            {
                "required_items": required_items,
                "team_members": self.work_permit.team_members.select_related("worker"),
                "verifications": self.work_permit.ppe_verifications.all()[:5],
            },
        )


class WizardChecklistView(DraftPermitMixin, View):
    step_slug = "checklist"

    def get(self, request, pk):
        self._ensure_checklist_seeded()
        return self._render(request)

    def post(self, request, pk):
        if "back" in request.POST:
            return self.go_previous(self.step_slug)
        if "advance" in request.POST:
            items = list(self.work_permit.checklist_items.all())
            valid_answers = {choice for choice, _ in PermitChecklistItem.Answer.choices}
            for item in items:
                submitted = request.POST.get(f"answer_{item.pk}", "")
                if submitted in valid_answers:
                    item.set_answer(submitted)

            if request.FILES.get("photo"):
                self.work_permit.photos.create(image=request.FILES["photo"])

            unanswered = [item for item in items if not item.answer]
            if unanswered:
                messages.error(request, "Responda todos os itens do checklist antes de avançar.")
                return redirect("permits:wizard_checklist", pk=pk)

            failing = [item for item in items if item.blocks_emission]
            if failing:
                failing_text = "; ".join(item.description for item in failing)
                messages.error(
                    request,
                    f"Corrija as condições marcadas como 'Não' antes de emitir a PET: {failing_text}",
                )
                return redirect("permits:wizard_checklist", pk=pk)

            return self.go_next(self.step_slug)
        return redirect("permits:wizard_checklist", pk=pk)

    def _ensure_checklist_seeded(self):
        if not self.work_permit.checklist_items.exists():
            services.seed_checklist_items(self.work_permit)

    def _render(self, request):
        items = self.work_permit.checklist_items.all()
        groups = {}
        for item in items:
            groups.setdefault(item.group_title, []).append(item)
        shows_confined_space_guidance = self.work_permit.risk_areas.filter(slug="confinado").exists()
        return self.wizard_render(
            request,
            self.step_slug,
            "checklist",
            {
                "groups": groups,
                "answer_choices": PermitChecklistItem.Answer.choices,
                "confined_space_guidance": CONFINED_SPACE_GENERAL_GUIDANCE
                if shows_confined_space_guidance
                else None,
            },
        )


class WizardSignaturesView(DraftPermitMixin, View):
    step_slug = "signatures"

    def get(self, request, pk):
        return self._render(request)

    def post(self, request, pk):
        if "back" in request.POST:
            return self.go_previous(self.step_slug)

        technician_data_url = request.POST.get("technician_signature", "")
        executor_worker_id = request.POST.get("executor_worker_id")
        executor_data_url = request.POST.get("executor_signature", "")
        if not technician_data_url or not executor_data_url or not executor_worker_id:
            messages.error(request, "Colete as duas assinaturas antes de emitir a PET.")
            return self._render(request)

        executor = get_object_or_404(
            Worker, pk=executor_worker_id, organization=self.work_permit.organization
        )
        latitude = request.POST.get("latitude") or None
        longitude = request.POST.get("longitude") or None

        self._save_signature(
            role=PermitSignature.Role.TECHNICIAN,
            full_name=request.user.get_full_name() or request.user.username,
            registration_number=request.user.registration_number,
            worker=getattr(request.user, "worker_profile", None),
            data_url=technician_data_url,
            latitude=latitude,
            longitude=longitude,
        )
        self._save_signature(
            role=PermitSignature.Role.EXECUTOR,
            full_name=executor.full_name,
            registration_number=executor.registration_number,
            worker=executor,
            data_url=executor_data_url,
            latitude=latitude,
            longitude=longitude,
        )

        services.submit_permit(self.work_permit, request.user)
        return redirect("permits:issued", pk=self.work_permit.pk)

    def _save_signature(self, role, full_name, registration_number, worker, data_url, latitude, longitude):
        signature = PermitSignature(
            work_permit=self.work_permit,
            role=role,
            worker=worker,
            full_name=full_name,
            registration_number=registration_number,
            latitude=latitude,
            longitude=longitude,
        )
        signature.signature_image = _decode_signature_image(data_url, f"{role}_{self.work_permit.pk}")
        signature.integrity_hash = signature.compute_integrity_hash()
        signature.save()
        return signature

    def _render(self, request):
        return self.wizard_render(
            request,
            self.step_slug,
            "signatures",
            {"team_members": self.work_permit.team_members.select_related("worker")},
        )


def _decode_signature_image(data_url, name):
    header, encoded = data_url.split(",", 1)
    return ContentFile(base64.b64decode(encoded), name=f"{name}.png")


class PermitIssuedView(TechnicianRequiredMixin, DetailView):
    model = WorkPermit
    template_name = "permits/permit_issued.html"
    context_object_name = "work_permit"

    def get_queryset(self):
        return WorkPermit.objects.filter(organization=self.request.user.organization)


class PermitDetailView(TechnicianRequiredMixin, DetailView):
    model = WorkPermit
    template_name = "permits/permit_detail.html"
    context_object_name = "work_permit"

    def get_queryset(self):
        return WorkPermit.objects.filter(organization=self.request.user.organization)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["gauge_specs"] = gas_measurement_specs(self.object.required_gas_measurement_keys)
        return context


class PermitCloseView(TechnicianRequiredMixin, View):
    def post(self, request, pk):
        work_permit = get_object_or_404(
            WorkPermit, pk=pk, organization=request.user.organization, status=WorkPermit.Status.OPEN
        )
        services.close_permit(work_permit, actor=request.user)
        messages.success(request, f"{work_permit.permit_number} encerrada.")
        return redirect("permits:detail", pk=pk)


class ApprovalQueueView(ManagerRequiredMixin, TemplateView):
    template_name = "permits/approval_queue.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        pending = WorkPermit.objects.filter(
            organization=self.request.user.organization, status=WorkPermit.Status.PENDING_APPROVAL
        ).select_related("unit", "requested_by").prefetch_related("risk_areas", "gas_readings")
        context["permits"] = priority_score.score_queue(pending)
        return context


class ApprovePermitView(ManagerRequiredMixin, View):
    def post(self, request, pk):
        work_permit = get_object_or_404(
            WorkPermit,
            pk=pk,
            organization=request.user.organization,
            status=WorkPermit.Status.PENDING_APPROVAL,
        )
        services.approve_permit(work_permit, request.user)
        messages.success(request, f"{work_permit.permit_number} aprovada e aberta.")
        return redirect("permits:approval_queue")


class RejectPermitView(ManagerRequiredMixin, View):
    def post(self, request, pk):
        work_permit = get_object_or_404(
            WorkPermit,
            pk=pk,
            organization=request.user.organization,
            status=WorkPermit.Status.PENDING_APPROVAL,
        )
        reason = request.POST.get("reason", "").strip() or "Sem motivo informado."
        services.reject_permit(work_permit, request.user, reason)
        messages.success(request, f"{work_permit.permit_number} rejeitada.")
        return redirect("permits:approval_queue")
