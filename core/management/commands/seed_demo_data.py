from datetime import date, timedelta

from django.core.management.base import BaseCommand

from accounts.models import User
from core.models import Unit
from workers.models import DocumentType, Worker, WorkerDocument


class Command(BaseCommand):
    help = "Creates a minimal set of demo users and a worker for local testing."

    def handle(self, *args, **options):
        unit, _ = Unit.objects.get_or_create(name="Matelândia")

        autonomous_tech, created = User.objects.get_or_create(
            username="tecnico.autonomo",
            defaults={
                "first_name": "Bárbara",
                "last_name": "Garlini",
                "role": User.Role.TECHNICIAN,
                "can_self_authorize": True,
                "unit": unit,
                "registration_number": "03177",
            },
        )
        if created:
            autonomous_tech.set_password("demo1234")
            autonomous_tech.save()
            self.stdout.write(self.style.SUCCESS("Created tecnico.autonomo / demo1234 (auto-emite PETs)"))

        supervised_tech, created = User.objects.get_or_create(
            username="tecnico.supervisionado",
            defaults={
                "first_name": "Rafael",
                "last_name": "Hoffmann",
                "role": User.Role.TECHNICIAN,
                "can_self_authorize": False,
                "unit": unit,
                "registration_number": "02988",
            },
        )
        if created:
            supervised_tech.set_password("demo1234")
            supervised_tech.save()
            self.stdout.write(self.style.SUCCESS("Created tecnico.supervisionado / demo1234 (depende de aprovação)"))

        manager, created = User.objects.get_or_create(
            username="gestor",
            defaults={
                "first_name": "Adriana",
                "last_name": "Beal",
                "role": User.Role.MANAGER,
                "unit": unit,
            },
        )
        if created:
            manager.set_password("demo1234")
            manager.save()
            self.stdout.write(self.style.SUCCESS("Created gestor / demo1234"))

        worker, created = Worker.objects.get_or_create(
            registration_number="04812",
            defaults={
                "full_name": "Jonas R. Kirchner",
                "job_title": "Mecânico industrial",
                "company": "Lar · Manutenção",
                "unit": unit,
                "employment_type": Worker.EmploymentType.OWN,
            },
        )
        if created:
            today = date.today()
            for code, days_ahead in [("ASO", 300), ("NR-33", 200), ("NR-35", 150)]:
                document_type = DocumentType.objects.get(code=code)
                WorkerDocument.objects.create(
                    worker=worker, document_type=document_type, valid_until=today + timedelta(days=days_ahead)
                )
            self.stdout.write(self.style.SUCCESS(f"Created worker {worker.full_name} (QR token {worker.qr_token})"))

        self.stdout.write(self.style.SUCCESS("Demo data ready."))
