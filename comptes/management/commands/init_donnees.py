from django.core.management.base import BaseCommand

from academique.models import AnneeAcademique, Filiere
from admissions.models import TypePiece


class Command(BaseCommand):
    help = "Crée les données fictives de base."

    def handle(self, *args, **options):
        AnneeAcademique.objects.get_or_create(libelle="2026-2027", defaults={"active": True})
        Filiere.objects.get_or_create(libelle="Génie informatique")
        pieces = [
            ("Acte de naissance", True),
            ("Relevé de notes du baccalauréat", True),
            ("Photo d'identité", True),
            ("Certificat de nationalité", False),
        ]
        for libelle, obligatoire in pieces:
            TypePiece.objects.get_or_create(libelle=libelle, defaults={"obligatoire": obligatoire})
        self.stdout.write(self.style.SUCCESS("Données fictives prêtes."))