from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import redirect, render
from django.views import View
from django.views.generic import ListView

from .forms import OrganizationOnboardingForm
from .mixins import SuperuserRequiredMixin
from .models import Organization
from .onboarding import provision_organization


class HomeRedirectView(LoginRequiredMixin, View):
    """Send a freshly logged-in user to the screen their role owns."""

    def get(self, request):
        user = request.user
        if user.role in (user.Role.MANAGER, user.Role.ADMIN):
            return redirect("dashboard:home")
        if user.role == user.Role.SAFETY_STAFF:
            return redirect("workers:list")
        return redirect("permits:home")


class OrganizationListView(SuperuserRequiredMixin, ListView):
    model = Organization
    template_name = "core/organization_list.html"
    context_object_name = "organizations"


class OrganizationCreateView(SuperuserRequiredMixin, View):
    """Onboards a brand-new tenant company — platform-level, not something
    a company's own admin can do (see core.mixins.SuperuserRequiredMixin)."""

    template_name = "core/organization_form.html"

    def get(self, request):
        return render(request, self.template_name, {"form": OrganizationOnboardingForm()})

    def post(self, request):
        form = OrganizationOnboardingForm(request.POST)
        if not form.is_valid():
            return render(request, self.template_name, {"form": form})

        organization, admin_user, raw_pin = provision_organization(
            name=form.cleaned_data["name"],
            cnpj=form.cleaned_data["cnpj"],
            unit_name=form.cleaned_data["unit_name"],
            unit_city=form.cleaned_data["unit_city"],
            unit_state=form.cleaned_data["unit_state"],
            admin_full_name=form.cleaned_data["admin_full_name"],
            admin_registration_number=form.cleaned_data["admin_registration_number"],
        )
        return render(
            request,
            "core/organization_created.html",
            {"organization": organization, "admin_user": admin_user, "raw_pin": raw_pin},
        )
