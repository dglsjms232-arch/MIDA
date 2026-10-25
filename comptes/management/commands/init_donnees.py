from django.core.management.base import BaseCommand

from academique.models import AnneeAcademique, Filiere, Niveau
from admissions.models import TypePiece


class Command(BaseCommand):
    help = "Crée les données fictives de base."

    def handle(self, *args, **options):
        AnneeAcademique.objects.get_or_create(libelle="2026-2027", defaults={"active": True})
        filiere, _ = Filiere.objects.get_or_create(libelle="Génie informatique")
        for libelle in ("Licence 1", "Licence 2", "Licence 3"):
            Niveau.objects.get_or_create(filiere=filiere, libelle=libelle)
        pieces = [
            ("Acte de naissance", True),
            ("Relevé de notes du baccalauréat", True),
            ("Photo d'identité", True),
            ("Certificat de nationalité", False),
        ]
        for libelle, obligatoire in pieces:
            TypePiece.objects.get_or_create(libelle=libelle, defaults={"obligatoire": obligatoire})
        self.stdout.write(self.style.SUCCESS("Données fictives prêtes."))