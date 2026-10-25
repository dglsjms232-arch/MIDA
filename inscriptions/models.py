from django.conf import settings
from django.db import models


class Inscription(models.Model):
    class Type(models.TextChoices):
        NOUVELLE = "nouvelle", "Nouvelle inscription"
        REINSCRIPTION = "reinscription", "Réinscription"

    class Statut(models.TextChoices):
        EN_COURS = "en_cours", "En cours"
        FINALISEE = "finalisee", "Finalisée"

    etudiant = models.ForeignKey("comptes.Etudiant", on_delete=models.PROTECT, related_name="inscriptions")
    annee = models.ForeignKey("academique.AnneeAcademique", on_delete=models.PROTECT)
    niveau = models.ForeignKey("academique.Niveau", on_delete=models.PROTECT)
    type = models.CharField(max_length=20, choices=Type.choices)
    statut = models.CharField(max_length=20, choices=Statut.choices, default=Statut.EN_COURS)
    finalisee_par = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL
    )
    date_finalisation = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"{self.etudiant} - {self.annee} ({self.get_statut_display()})"


class DecisionReprise(models.Model):
    inscription = models.ForeignKey(Inscription, on_delete=models.CASCADE, related_name="decisions_reprise")
    responsable = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    date = models.DateTimeField(auto_now_add=True)
    motif = models.TextField()


class MatiereReprise(models.Model):
    decision = models.ForeignKey(DecisionReprise, on_delete=models.CASCADE, related_name="matieres")
    dette = models.ForeignKey("academique.Dette", on_delete=models.PROTECT)

    class Meta:
        unique_together = ("decision", "dette")
