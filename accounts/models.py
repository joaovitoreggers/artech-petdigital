from django.contrib.auth.models import AbstractUser
from django.db import models

from . import pin as pin_utils


class User(AbstractUser):
    """The system's login identity.

    The operational app (everything except Django's own /admin/) is
    authenticated by PIN, not username/password — see accounts.backends
    and accounts.pin. `role` drives which screens a user can reach (see
    core.mixins) and `can_self_authorize` decides whether a technician's
    permits open immediately or wait for a manager's approval
    (permits.services.submit_permit).
    """

    class Role(models.TextChoices):
        TECHNICIAN = "technician", "Técnico de segurança"
        MANAGER = "manager", "Gestor"
        SAFETY_STAFF = "safety_staff", "SESMT / RH"
        ADMIN = "admin", "Administrador"

    role = models.CharField(max_length=20, choices=Role.choices, default=Role.TECHNICIAN)
    can_self_authorize = models.BooleanField(
        "pode autoemitir PETs",
        default=False,
        help_text="Se marcado, as PETs deste técnico abrem direto após as assinaturas, sem aprovação de um gestor.",
    )
    organization = models.ForeignKey(
        "core.Organization", on_delete=models.CASCADE, null=True, blank=True, related_name="users"
    )
    unit = models.ForeignKey(
        "core.Unit", on_delete=models.SET_NULL, null=True, blank=True, related_name="users"
    )
    registration_number = models.CharField("matrícula", max_length=20, blank=True)

    pin_hash = models.CharField(max_length=64, unique=True, null=True, blank=True, editable=False)
    pin_set_at = models.DateTimeField(null=True, blank=True, editable=False)

    def __str__(self):
        return self.get_full_name() or self.username

    @property
    def has_pin(self):
        return bool(self.pin_hash)

    def set_pin(self, raw_pin=None):
        """Hash and store a login PIN, generating one if not given.

        Returns the plaintext PIN — the only moment it exists outside the
        hash, since the hash can't be reversed. Callers must show/hand it
        to the user right away; it's never retrievable again afterwards.
        """
        from django.utils import timezone

        raw_pin = raw_pin or pin_utils.generate_raw_pin()
        candidate_hash = pin_utils.hash_pin(raw_pin)
        while User.objects.exclude(pk=self.pk).filter(pin_hash=candidate_hash).exists():
            raw_pin = pin_utils.generate_raw_pin()
            candidate_hash = pin_utils.hash_pin(raw_pin)
        self.pin_hash = candidate_hash
        self.pin_set_at = timezone.now()
        self.save(update_fields=["pin_hash", "pin_set_at"])
        return raw_pin

    @classmethod
    def get_by_pin(cls, raw_pin):
        try:
            return cls.objects.get(pin_hash=pin_utils.hash_pin(raw_pin), is_active=True)
        except cls.DoesNotExist:
            return None
