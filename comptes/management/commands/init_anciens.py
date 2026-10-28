from django.core.management.base import BaseCommand

from academique.models import (
    AnneeAcademique, Filiere, LigneReleve, Matiere, Niveau, ReleveNotes,
)
from academique.services import creer_dettes
from comptes.models import Etudiant

# Données fictives : 10 matières de 6 crédits = 60 crédits.
MATIERES = [
    ("INF201", "Algorithmique avancée"), ("INF202", "Bases de données"),
    ("INF203", "Programmation Java"), ("INF204", "Probabilités"),
    ("INF205", "Statistiques"), ("INF206", "Réseaux"),
    ("INF207", "Systèmes d'exploitation"), ("INF208", "Génie logiciel"),
    ("MAT201", "Algèbre linéaire"), ("ANG201", "Anglais technique"),
]

# (matricule, nom, prénom, matières non validées)
ANCIENS = [
    ("UCAO-2025-0101", "KOFFI", "Ama", []),
    ("UCAO-2025-0102", "MENSAH", "Yao", ["INF205", "INF206"]),
    ("UCAO-2025-0103", "AGBO", "Kossi", ["INF202", "INF203", "INF204", "INF208", "MAT201"]),
    ("UCAO-2025-0104", "TOGBE", "Efua", ["INF207", "INF208", "MAT201"]),
]


class Command(BaseCommand):
    help = "Importe trois anciens étudiants fictifs avec leur relevé de notes."

    def handle(self, *args, **options):
        filiere, _ = Filiere.objects.get_or_create(libelle="Génie informatique")
        niveau, _ = Niveau.objects.get_or_create(filiere=filiere, libelle="Licence 2")
        annee, _ = AnneeAcademique.objects.get_or_create(libelle="2025-2026", defaults={"active": False})

        matieres = {}
        for code, intitule in MATIERES:
            m, _ = Matiere.objects.get_or_create(
                code=code, defaults={"intitule": intitule, "credits": 6, "niveau": niveau}
            )
            matieres[code] = m

        for matricule, nom, prenom, echecs in ANCIENS:
            etudiant, _ = Etudiant.objects.get_or_create(
                matricule=matricule, defaults={"nom": nom, "prenom": prenom}
            )
            if ReleveNotes.objects.filter(etudiant=etudiant, annee=annee).exists():
                continue
            releve = ReleveNotes.objects.create(
                etudiant=etudiant, annee=annee, niveau=niveau,
                credits_obtenus=60 - 6 * len(echecs),
            )
            for code, m in matieres.items():
                validee = code not in echecs
                LigneReleve.objects.create(
                    releve=releve, matiere=m, validee=validee, note=12.5 if validee else 7.5
                )
            creer_dettes(releve)
            self.stdout.write(f"{nom} {prenom} : {releve.credits_obtenus} crédits")
        self.stdout.write(self.style.SUCCESS("Anciens étudiants fictifs importés."))