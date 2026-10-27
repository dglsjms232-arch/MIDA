from django.core.management.base import BaseCommand

from academique.models import AnneeAcademique, Filiere, Niveau
from admissions.models import TypePiece
from paiements.models import Tarif


class Command(BaseCommand):
    help = "Crée les données fictives de base."

    def handle(self, *args, **options):
        annee, _ = AnneeAcademique.objects.get_or_create(libelle="2026-2027", defaults={"active": True})
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
        # Tarifs fictifs : hypothèses à faire valider.
        Tarif.objects.get_or_create(
            libelle="Première tranche", type=Tarif.Type.PREMIERE_TRANCHE, annee=annee,
            defaults={"montant": 100000},
        )
        Tarif.objects.get_or_create(
            libelle="Matière à reprendre", type=Tarif.Type.MATIERE_REPRISE, annee=annee,
            defaults={"montant": 15000},
        )
        self.stdout.write(self.style.SUCCESS("Données fictives prêtes."))