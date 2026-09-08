import re
from collections import defaultdict

from django.db import migrations

NUMBER_PATTERN = re.compile(r"^PET-(\d{4})-(\d+)$")


def seed_data(apps, schema_editor):
    """Start each year's counter at the highest sequence number already
    used, not at the row count — existing permits may have gaps from
    deletions, and the counter must never reissue a number still in use."""
    WorkPermit = apps.get_model("permits", "WorkPermit")
    PermitSequenceCounter = apps.get_model("permits", "PermitSequenceCounter")

    max_by_year = defaultdict(int)
    for permit_number in WorkPermit.objects.values_list("permit_number", flat=True):
        match = NUMBER_PATTERN.match(permit_number)
        if not match:
            continue
        year, number = int(match.group(1)), int(match.group(2))
        max_by_year[year] = max(max_by_year[year], number)

    for year, last_number in max_by_year.items():
        PermitSequenceCounter.objects.update_or_create(year=year, defaults={"last_number": last_number})


def remove_data(apps, schema_editor):
    PermitSequenceCounter = apps.get_model("permits", "PermitSequenceCounter")
    PermitSequenceCounter.objects.all().delete()


class Migration(migrations.Migration):
    dependencies = [("permits", "0007_permitsequencecounter")]
    operations = [migrations.RunPython(seed_data, remove_data)]
