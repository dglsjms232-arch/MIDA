from django.apps import apps
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Affiche le nombre d'enregistrements par table métier."

    def handle(self, *args, **options):
        for app in ("comptes", "academique", "admissions", "inscriptions", "paiements", "historique"):
            for modele in apps.get_app_config(app).get_models():
                self.stdout.write(f"{modele._meta.label:40} {modele.objects.count()}")
        User = get_user_model()
        self.stdout.write(f"{'auth.User':40} {User.objects.count()}")