from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models


class Tarif(models.Model):
    class Type(models.TextChoices):
        PREMIERE_TRANCHE = "premiere_tranche", "Première tranche"
        MATIERE_REPRISE = "matiere_reprise", "Matière à reprendre"

    libelle = models.CharField(max_length=100)
    type = models.CharField(max_length=20, choices=Type.choices)
    montant = models.DecimalField(max_digits=10, decimal_places=0)  # données fictives
    niveau = models.ForeignKey("academique.Niveau", null=True, blank=True, on_delete=models.PROTECT)
    annee = models.ForeignKey("academique.AnneeAcademique", on_delete=models.PROTECT)

    def __str__(self):
        return f"{self.libelle} - {self.montant}"


class Justificatif(models.Model):
    class Objet(models.TextChoices):
        PREMIERE_TRANCHE = "premiere_tranche", "Première tranche"
        MATIERE_REPRISE = "matiere_reprise", "Matière à reprendre"

    class Statut(models.TextChoices):
        EN_ATTENTE = "en_attente", "En attente"
        ACCEPTE = "accepte", "Accepté"
        REFUSE = "refuse", "Refusé"

    etudiant = models.ForeignKey("comptes.Etudiant", on_delete=models.PROTECT, related_name="justificatifs")
    objet = models.CharField(max_length=20, choices=Objet.choices)
    dette = models.ForeignKey("academique.Dette", null=True, blank=True, on_delete=models.PROTECT)
    fichier = models.FileField(upload_to="justificatifs/")
    montant_declare = models.DecimalField(max_digits=10, decimal_places=0)
    reference_bancaire = models.CharField(max_length=50)
    statut = models.CharField(max_length=20, choices=Statut.choices, default=Statut.EN_ATTENTE)
    motif_refus = models.TextField(blank=True)
    verifie_par = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL
    )
    date_depot = models.DateTimeField(auto_now_add=True)
    date_verification = models.DateTimeField(null=True, blank=True)

    def clean(self):
        # Un justificatif refusé doit toujours avoir un motif.
        if self.statut == self.Statut.REFUSE and not self.motif_refus.strip():
            raise ValidationError("Un motif est obligatoire pour refuser un justificatif.")