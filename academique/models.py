from django.conf import settings
from django.core.validators import MaxValueValidator
from django.db import models


class AnneeAcademique(models.Model):
    libelle = models.CharField(max_length=20, unique=True)  # ex : 2025-2026
    active = models.BooleanField(default=False)

    def __str__(self):
        return self.libelle


class Filiere(models.Model):
    libelle = models.CharField(max_length=100, unique=True)

    def __str__(self):
        return self.libelle


class Niveau(models.Model):
    filiere = models.ForeignKey(Filiere, on_delete=models.PROTECT, related_name="niveaux")
    libelle = models.CharField(max_length=50)  # ex : Licence 2

    def __str__(self):
        return f"{self.filiere} - {self.libelle}"


class Matiere(models.Model):
    code = models.CharField(max_length=20, unique=True)
    intitule = models.CharField(max_length=150)
    credits = models.PositiveSmallIntegerField()
    niveau = models.ForeignKey(Niveau, on_delete=models.PROTECT, related_name="matieres")

    def __str__(self):
        return f"{self.code} - {self.intitule}"


class ReleveNotes(models.Model):
    etudiant = models.ForeignKey("comptes.Etudiant", on_delete=models.PROTECT, related_name="releves")
    annee = models.ForeignKey(AnneeAcademique, on_delete=models.PROTECT)
    niveau = models.ForeignKey(Niveau, on_delete=models.PROTECT)
    credits_obtenus = models.PositiveSmallIntegerField(validators=[MaxValueValidator(60)])
    saisi_par = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL)
    date_saisie = models.DateTimeField(auto_now_add=True)

    @property
    def situation(self):
        """60 crédits / de 40 à 59 / moins de 40 (jamais de validation automatique)."""
        if self.credits_obtenus >= 60:
            return "complet"
        if self.credits_obtenus >= 40:
            return "reinscription"
        return "decision_institutionnelle"

    def __str__(self):
        return f"{self.etudiant} - {self.annee} ({self.credits_obtenus}/60)"


class LigneReleve(models.Model):
    releve = models.ForeignKey(ReleveNotes, on_delete=models.CASCADE, related_name="lignes")
    matiere = models.ForeignKey(Matiere, on_delete=models.PROTECT)
    note = models.DecimalField(max_digits=4, decimal_places=2, null=True, blank=True)
    validee = models.BooleanField(default=False)


class Dette(models.Model):
    class Statut(models.TextChoices):
        NON_VALIDEE = "non_validee", "Non validée"
        RETENUE = "retenue", "Retenue pour reprise"
        NON_RETENUE = "non_retenue", "Non retenue"
        REGULARISEE = "regularisee", "Régularisée"

    etudiant = models.ForeignKey("comptes.Etudiant", on_delete=models.PROTECT, related_name="dettes")
    matiere = models.ForeignKey(Matiere, on_delete=models.PROTECT)
    annee_origine = models.ForeignKey(AnneeAcademique, on_delete=models.PROTECT)
    statut = models.CharField(max_length=20, choices=Statut.choices, default=Statut.NON_VALIDEE)

    def __str__(self):
        return f"{self.etudiant} - {self.matiere} ({self.get_statut_display()})"