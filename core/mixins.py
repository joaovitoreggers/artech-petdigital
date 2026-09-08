from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin


class RoleRequiredMixin(LoginRequiredMixin, UserPassesTestMixin):
    """Restrict a view to one or more `accounts.User.Role` values.

    Subclasses set `allowed_roles`. Superusers always pass (platform-wide,
    every organization); a company's own `admin` role always passes too,
    scoped to their own organization by the view's own queryset filtering —
    the company admin is meant to reach every screen their own company has.
    """

    allowed_roles: tuple[str, ...] = ()
    raise_exception = False

    def test_func(self):
        user = self.request.user
        return user.is_superuser or user.role == user.Role.ADMIN or user.role in self.allowed_roles

    def handle_no_permission(self):
        if self.request.user.is_authenticated:
            from django.contrib import messages

            messages.error(self.request, "Você não tem permissão para acessar esta página.")
            from django.shortcuts import redirect

            return redirect("core:home")
        return super().handle_no_permission()


class TechnicianRequiredMixin(RoleRequiredMixin):
    allowed_roles = ("technician",)


class ManagerRequiredMixin(RoleRequiredMixin):
    allowed_roles = ("manager",)


class SafetyStaffRequiredMixin(RoleRequiredMixin):
    """Workers registry (Funcionários) is managed by SESMT/HR staff or managers."""

    allowed_roles = ("safety_staff", "manager")


class CredentialManagerRequiredMixin(RoleRequiredMixin):
    """Issuing/regenerating login PINs is a SESMT/HR/manager/admin duty."""

    allowed_roles = ("safety_staff", "manager", "admin")


class SuperuserRequiredMixin(LoginRequiredMixin, UserPassesTestMixin):
    """Platform-level screens (registering a new tenant company) — not a
    company-level 'admin' role, which stays scoped to its own organization."""

    raise_exception = False

    def test_func(self):
        return self.request.user.is_superuser

    def handle_no_permission(self):
        if self.request.user.is_authenticated:
            from django.contrib import messages
            from django.shortcuts import redirect

            messages.error(self.request, "Você não tem permissão para acessar esta página.")
            return redirect("core:home")
        return super().handle_no_permission()
