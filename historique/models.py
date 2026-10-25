from django.conf import settings
from django.db import models


class JournalAction(models.Model):
    auteur = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL)
    date = models.DateTimeField(auto_now_add=True)
    action = models.CharField(max_length=100)
    objet = models.CharField(max_length=200)  # ex : "Demande 12"
    motif = models.TextField(blank=True)

    class Meta:
        ordering = ["-date"]