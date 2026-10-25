from django.conf import settings
from django.db import models


class TypePiece(models.Model):
    libelle = models.CharField(max_length=100, unique=True)
    obligatoire = models.BooleanField(default=True)

    def __str__(self):
        return self.libelle


class Demande(models.Model):
    class Mode(models.TextChoices):
        NUMERIQUE = "numerique", "Dépôt en ligne"
        PHYSIQUE = "physique", "Dépôt physique"

    class Statut(models.TextChoices):
        SOUMISE = "soumise", "Soumise"
        INCOMPLETE = "incomplete", "Dossier incomplet"
        EN_ETUDE = "en_etude", "En étude"
        ADMISE = "admise", "Admise"
        REFUSEE = "refusee", "Refusée"

    etudiant = models.ForeignKey("comptes.Etudiant", on_delete=models.PROTECT, related_name="demandes")
    annee = models.ForeignKey("academique.AnneeAcademique", on_delete=models.PROTECT)
    filiere = models.ForeignKey("academique.Filiere", on_delete=models.PROTECT)
    mode_depot = models.CharField(max_length=20, choices=Mode.choices, default=Mode.NUMERIQUE)
    statut = models.CharField(max_length=20, choices=Statut.choices, default=Statut.SOUMISE)
    enregistree_par = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL
    )
    date_creation = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Demande {self.id} - {self.etudiant} ({self.get_statut_display()})"


class PieceJointe(models.Model):
    demande = models.ForeignKey(Demande, on_delete=models.CASCADE, related_name="pieces")
    type_piece = models.ForeignKey(TypePiece, on_delete=models.PROTECT)
    fichier = models.FileField(upload_to="pieces/")
    date_depot = models.DateTimeField(auto_now_add=True)


class DecisionAdmission(models.Model):
    class Resultat(models.TextChoices):
        ADMIS = "admis", "Admis"
        REFUSE = "refuse", "Refusé"

    demande = models.ForeignKey(Demande, on_delete=models.CASCADE, related_name="decisions")
    resultat = models.CharField(max_length=10, choices=Resultat.choices)
    auteur = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    date = models.DateTimeField(auto_now_add=True)
    motif = models.TextField(blank=True)


class Communication(models.Model):
    class Canal(models.TextChoices):
        SMS = "sms", "SMS"
        EMAIL = "email", "E-mail"
        APPEL = "appel", "Appel"
        SUR_PLACE = "sur_place", "Sur place"

    demande = models.ForeignKey(Demande, on_delete=models.CASCADE, related_name="communications")
    canal = models.CharField(max_length=20, choices=Canal.choices)
    date = models.DateTimeField(auto_now_add=True)
    auteur = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    resume = models.TextField()