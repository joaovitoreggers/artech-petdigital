from django import template
from django.utils import timezone

from core.constants import DOCUMENT_EXPIRY_WARNING_DAYS

register = template.Library()


@register.filter
def days_until(value):
    """Days between today and a date (negative if the date is in the past)."""
    if not value:
        return None
    return (value - timezone.localdate()).days


@register.filter
def expiry_status(value):
    """Classify a validity date as 'valid' / 'expiring_soon' / 'expired'."""
    remaining = days_until(value)
    if remaining is None:
        return "missing"
    if remaining < 0:
        return "expired"
    if remaining <= DOCUMENT_EXPIRY_WARNING_DAYS:
        return "expiring_soon"
    return "valid"


@register.filter
def expiry_badge_class(value):
    return {
        "valid": "status-ok",
        "expiring_soon": "status-warning",
        "expired": "status-danger",
        "missing": "status-neutral",
    }[expiry_status(value)]


@register.filter
def get_attr(obj, attr_name):
    """Dynamic attribute lookup for templates — `{{ obj|get_attr:name_var }}` —
    since Django's `.` lookup can't take the attribute name from a variable."""
    if obj is None:
        return None
    return getattr(obj, attr_name, None)
