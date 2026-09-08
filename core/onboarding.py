"""Provisions a brand-new tenant company end to end — called by
core.views.OrganizationCreateView. Every new organization starts from the
same NR reference content the platform ships with (permits.constants,
workers.constants) and can edit its own copy afterwards through the admin.

Uses local (in-function) imports of `workers` and `permits` so this module
can stay in `core` without creating an import cycle — both of those apps
already import from `core.models`.
"""

from django.db import transaction
from django.utils.text import slugify

from .models import Organization, RiskArea, Unit


def _unique_slug(name):
    base = slugify(name)
    slug = base
    suffix = 2
    while Organization.objects.filter(slug=slug).exists():
        slug = f"{base}-{suffix}"
        suffix += 1
    return slug


def _unique_username(user_model, name, organization_slug):
    """Usernames are unique platform-wide (Django's default), so two
    organizations onboarding a same-named admin can't collide — fold the
    org slug in as a tiebreaker rather than a random suffix, so it stays
    predictable/legible."""
    base = slugify(name) or "admin"
    candidate = f"{base}.{organization_slug}"
    username = candidate
    suffix = 2
    while user_model.objects.filter(username=username).exists():
        username = f"{candidate}-{suffix}"
        suffix += 1
    return username


def provision_organization(
    *, name, cnpj, unit_name, unit_city, unit_state, admin_full_name, admin_registration_number
):
    """Creates the Organization, seeds its NR reference content, creates
    its first Unit and first admin User. Returns (organization, admin_user,
    raw_pin) — the PIN is only ever available here, right after creation;
    show it to the caller once and never again (see accounts.User.set_pin)."""
    from accounts.models import User
    from permits.constants import DEFAULT_RISK_AREAS, RISK_AREA_CHECKLISTS, RISK_AREA_MANDATORY_PPE
    from permits.models import ChecklistItemTemplate, MandatoryPPEItem
    from workers.constants import DEFAULT_DOCUMENT_TYPES
    from workers.models import DocumentType

    with transaction.atomic():
        organization = Organization.objects.create(name=name, slug=_unique_slug(name), cnpj=cnpj)

        risk_areas_by_slug = {}
        for data in DEFAULT_RISK_AREAS:
            risk_areas_by_slug[data["slug"]] = RiskArea.objects.create(organization=organization, **data)

        for data in DEFAULT_DOCUMENT_TYPES:
            DocumentType.objects.create(organization=organization, **data)

        checklist_order = 0
        for slug, groups in RISK_AREA_CHECKLISTS.items():
            risk_area = risk_areas_by_slug.get(slug)
            if risk_area is None:
                continue
            for group in groups:
                for description, regulatory_code in group["items"]:
                    ChecklistItemTemplate.objects.create(
                        organization=organization,
                        risk_area=risk_area,
                        group_title=group["group_title"],
                        description=description,
                        regulatory_code=regulatory_code,
                        order=checklist_order,
                    )
                    checklist_order += 1

        for slug, items in RISK_AREA_MANDATORY_PPE.items():
            risk_area = risk_areas_by_slug.get(slug)
            if risk_area is None:
                continue
            for order, description in enumerate(items):
                MandatoryPPEItem.objects.create(
                    organization=organization, risk_area=risk_area, description=description, order=order
                )

        unit = Unit.objects.create(
            organization=organization, name=unit_name, city=unit_city, state=unit_state
        )

        admin_user = User.objects.create(
            username=_unique_username(User, admin_full_name, organization.slug),
            first_name=admin_full_name.split(" ")[0],
            last_name=" ".join(admin_full_name.split(" ")[1:]),
            role=User.Role.ADMIN,
            can_self_authorize=True,
            organization=organization,
            unit=unit,
            registration_number=admin_registration_number,
        )
        admin_user.set_unusable_password()
        admin_user.save(update_fields=["password"])
        raw_pin = admin_user.set_pin()

    return organization, admin_user, raw_pin
