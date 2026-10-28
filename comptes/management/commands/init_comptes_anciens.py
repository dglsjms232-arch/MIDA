from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.management.base import BaseCommand

from comptes.models import Etudiant

COMPTES = [
    ("UCAO-2025-0101", "koffi"),
    ("UCAO-2025-0102", "mensah"),
    ("UCAO-2025-0103", "agbo"),
    ("UCAO-2025-0104", "togbe"),
]


class Command(BaseCommand):
    help = "Crée un compte de démonstration pour chaque ancien étudiant fictif."

    def handle(self, *args, **options):
        User = get_user_model()
        groupe, _ = Group.objects.get_or_create(name="Candidat")
        for matricule, identifiant in COMPTES:
            etudiant = Etudiant.objects.filter(matricule=matricule).first()
            if etudiant is None:
                continue
            user, _ = User.objects.get_or_create(username=identifiant)
            user.set_password("Demo2026!")
            user.save()
            user.groups.add(groupe)
            etudiant.user = user
            etudiant.save()
            self.stdout.write(f"{identifiant} -> {etudiant}")
        self.stdout.write(self.style.SUCCESS("Comptes des anciens étudiants prêts."))