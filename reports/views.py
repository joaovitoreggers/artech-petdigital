from django.core.files.base import ContentFile
from django.http import FileResponse
from django.shortcuts import render
from django.views import View

from core.mixins import ManagerRequiredMixin

from .forms import PeriodReportForm
from .models import PeriodReport
from .services import build_report_context, render_report_pdf


class PeriodReportCreateView(ManagerRequiredMixin, View):
    template_name = "reports/period_report_form.html"

    def get(self, request):
        return render(request, self.template_name, {"form": PeriodReportForm(organization=request.user.organization)})

    def post(self, request):
        form = PeriodReportForm(request.POST, organization=request.user.organization)
        if not form.is_valid():
            return render(request, self.template_name, {"form": form})

        period_start = form.cleaned_data["period_start"]
        period_end = form.cleaned_data["period_end"]
        unit = form.cleaned_data["unit"]

        context = build_report_context(request.user.organization, period_start, period_end, unit, request.user)
        pdf_bytes = render_report_pdf(context)

        report = PeriodReport.objects.create(
            organization=request.user.organization,
            unit=unit,
            period_start=period_start,
            period_end=period_end,
            generated_by=request.user,
        )
        filename = f"pet-digital-{period_start}-a-{period_end}.pdf"
        report.pdf_file.save(filename, ContentFile(pdf_bytes), save=True)

        return FileResponse(report.pdf_file.open("rb"), as_attachment=True, filename=filename)
