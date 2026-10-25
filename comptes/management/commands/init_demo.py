from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.management.base import BaseCommand

ROLES = {
    "candidat": "Candidat",
    "admissions": "Admissions",
    "scolarite": "Scolarité",
    "pedagogique": "Responsable pédagogique",
    "paiements": "Agent paiements",
    "admin": "Administrateur",
}
MOT_DE_PASSE = "Demo2026!"  # mot de passe fictif, réservé à la démonstration


class Command(BaseCommand):
    help = "Crée les groupes de rôles et les comptes de démonstration."

    def handle(self, *args, **options):
        User = get_user_model()
        for identifiant, nom_groupe in ROLES.items():
            groupe, _ = Group.objects.get_or_create(name=nom_groupe)
            user, _ = User.objects.get_or_create(username=identifiant)
            user.set_password(MOT_DE_PASSE)
            if identifiant == "admin":
                user.is_staff = True
                user.is_superuser = True
            user.save()
            user.groups.add(groupe)
            self.stdout.write(f"{identifiant} -> {nom_groupe}")
        self.stdout.write(self.style.SUCCESS("Comptes de démonstration prêts."))