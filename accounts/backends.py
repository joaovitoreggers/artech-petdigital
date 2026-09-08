from django.contrib.auth import get_user_model

from .pin import is_valid_pin_format


class PinBackend:
    """Authenticates by PIN alone — no username, no password.

    Registered in AUTHENTICATION_BACKENDS alongside Django's ModelBackend
    (which keeps handling /admin/'s own username/password login); this
    backend only ever matches calls made with a `pin` keyword, which is all
    accounts.views.LoginView passes.
    """

    def authenticate(self, request, pin=None, **kwargs):
        if not pin or not is_valid_pin_format(pin):
            return None
        return get_user_model().get_by_pin(pin)

    def get_user(self, user_id):
        UserModel = get_user_model()
        try:
            return UserModel.objects.get(pk=user_id)
        except UserModel.DoesNotExist:
            return None
