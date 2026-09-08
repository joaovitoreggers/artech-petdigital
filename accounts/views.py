from django.contrib import messages
from django.contrib.auth import authenticate, login
from django.contrib.auth.views import LogoutView as DjangoLogoutView
from django.shortcuts import get_object_or_404, redirect, render
from django.views import View
from django.views.generic import ListView

from core.mixins import CredentialManagerRequiredMixin

from . import throttling
from .forms import PinLoginForm
from .models import User


class LoginView(View):
    """PIN-only login for the operational app.

    Django's own /admin/ keeps its separate username/password form
    (ModelBackend, still enabled in AUTHENTICATION_BACKENDS) — this view is
    only the entry point for the technician/manager/SESMT screens.
    """

    template_name = "accounts/login.html"

    def get(self, request):
        if request.user.is_authenticated:
            return redirect("core:home")
        return render(request, self.template_name, {"form": PinLoginForm()})

    def post(self, request):
        if throttling.is_locked_out(request):
            messages.error(request, "Muitas tentativas com PIN incorreto. Aguarde alguns minutos e tente novamente.")
            return render(request, self.template_name, {"form": PinLoginForm()})

        form = PinLoginForm(request.POST)
        if form.is_valid():
            user = authenticate(request, pin=form.cleaned_data["pin"])
            if user is not None:
                login(request, user)
                throttling.reset_attempts(request)
                return redirect("core:home")

        throttling.register_failed_attempt(request)
        messages.error(request, "PIN inválido.")
        return render(request, self.template_name, {"form": PinLoginForm()})


class LogoutView(DjangoLogoutView):
    pass


class PinManagementView(CredentialManagerRequiredMixin, ListView):
    """List every user's PIN status and let SESMT/managers (re)issue one."""

    model = User
    template_name = "accounts/pin_management.html"
    context_object_name = "users"

    def get_queryset(self):
        return User.objects.filter(organization=self.request.user.organization).select_related(
            "unit"
        ).order_by("first_name", "last_name", "username")


class GeneratePinView(CredentialManagerRequiredMixin, View):
    def post(self, request, pk):
        user = get_object_or_404(User, pk=pk, organization=request.user.organization)
        raw_pin = user.set_pin()
        messages.success(
            request,
            f"Novo PIN para {user}: {raw_pin} — anote agora e entregue ao colaborador. "
            "Ele não será mostrado novamente.",
        )
        return redirect("accounts:pin_management")
