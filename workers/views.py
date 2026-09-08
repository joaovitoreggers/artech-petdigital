import io

import qrcode
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db import transaction
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views import View
from django.views.generic import ListView

from core.mixins import SafetyStaffRequiredMixin
from core.models import Unit

from . import document_extraction
from .forms import WorkerForm, build_document_formset
from .models import Worker


class WorkerListView(SafetyStaffRequiredMixin, ListView):
    """Desktop 'Funcionários' screen: KPI tiles + filters + table."""

    model = Worker
    template_name = "workers/worker_list.html"
    context_object_name = "workers"
    paginate_by = 50

    def get_queryset(self):
        queryset = Worker.objects.filter(organization=self.request.user.organization).select_related(
            "unit"
        ).prefetch_related("documents__document_type")
        status = self.request.GET.get("status")
        unit_id = self.request.GET.get("unit")
        if unit_id:
            queryset = queryset.filter(unit_id=unit_id)
        if status:
            queryset = [w for w in queryset if w.overall_status == status]
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        all_workers = list(
            Worker.objects.filter(organization=self.request.user.organization).prefetch_related("documents")
        )
        context["kpis"] = {
            "total": len(all_workers),
            "valid": sum(1 for w in all_workers if w.overall_status == "valid"),
            "expiring_soon": sum(1 for w in all_workers if w.overall_status == "expiring_soon"),
            "expired": sum(1 for w in all_workers if w.overall_status == "expired"),
        }
        context["units"] = Unit.objects.filter(organization=self.request.user.organization)
        context["selected_status"] = self.request.GET.get("status", "")
        context["selected_unit"] = self.request.GET.get("unit", "")
        return context


class WorkerCreateView(LoginRequiredMixin, View):
    """Register a worker + their document validity dates in one screen.

    Mirrors the prototype's 'Cadastrar funcionário' dialog: one form per
    known document type, blank meaning "not tracked for this worker".
    """

    template_name = "workers/worker_form.html"

    def get(self, request):
        organization = request.user.organization
        return render(
            request,
            self.template_name,
            {
                "form": WorkerForm(organization=organization),
                "document_formset": build_document_formset(organization=organization),
            },
        )

    def post(self, request):
        organization = request.user.organization
        form = WorkerForm(request.POST, organization=organization)
        document_formset = build_document_formset(organization=organization, data=request.POST)
        if form.is_valid() and document_formset.is_valid():
            with transaction.atomic():
                worker = form.save(commit=False)
                worker.organization = organization
                worker.save()
                for document_form in document_formset:
                    valid_until = document_form.cleaned_data.get("valid_until")
                    if valid_until:
                        document_type = document_form.cleaned_data["document_type"]
                        worker.documents.create(document_type=document_type, valid_until=valid_until)
            messages.success(request, f"Funcionário {worker.full_name} cadastrado. Crachá QR gerado.")
            return redirect("workers:list")
        return render(
            request, self.template_name, {"form": form, "document_formset": document_formset}
        )


class DocumentValidityExtractView(LoginRequiredMixin, View):
    """AJAX helper for the worker registration form: reads a candidate
    expiry date off a photographed document so whoever is registering the
    worker can review/correct it instead of typing it from scratch. Never
    saves anything by itself — the human still submits the form."""

    def post(self, request):
        photo = request.FILES.get("photo")
        if not photo:
            return JsonResponse({"success": False, "error": "Nenhuma foto enviada."}, status=400)

        document_label = request.POST.get("document_label", "documento").strip() or "documento"
        try:
            result = document_extraction.extract_document_validity(photo.read(), document_label)
        except document_extraction.DocumentExtractionError as exc:
            return JsonResponse({"success": False, "error": str(exc)}, status=502)

        if not result["valid_until"]:
            return JsonResponse(
                {"success": False, "error": result["notes"] or "Não foi possível ler a validade nessa foto."}
            )
        return JsonResponse(
            {
                "success": True,
                "valid_until": result["valid_until"].isoformat(),
                "confidence": result["confidence"],
                "notes": result["notes"],
            }
        )


class WorkerBadgeView(LoginRequiredMixin, View):
    """Printable 'crachá' page for one worker — name/role/unit plus the QR
    code that gets scanned in the field wizard's team-assembly step."""

    def get(self, request, pk):
        worker = get_object_or_404(Worker, pk=pk, organization=request.user.organization)
        return render(request, "workers/worker_badge.html", {"worker": worker})


class WorkerBadgeQRView(LoginRequiredMixin, View):
    """The worker's QR code alone, as a PNG — embedded as an <img> in the
    printable badge page above."""

    def get(self, request, pk):
        worker = get_object_or_404(Worker, pk=pk, organization=request.user.organization)
        payload = str(worker.qr_token)
        image = qrcode.make(payload)
        buffer = io.BytesIO()
        image.save(buffer, format="PNG")
        return HttpResponse(buffer.getvalue(), content_type="image/png")
