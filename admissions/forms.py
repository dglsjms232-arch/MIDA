import os

from django import forms
from django.core.exceptions import ValidationError

from academique.models import Filiere

from .models import TypePiece


def valider_fichier(f):
    if os.path.splitext(f.name)[1].lower() not in {".pdf", ".jpg", ".jpeg", ".png"}:
        raise ValidationError("Formats acceptés : PDF, JPG, PNG.")
    if f.size > 5 * 1024 * 1024:
        raise ValidationError("Fichier trop volumineux (5 Mo maximum).")


class DemandeForm(forms.Form):
    nom = forms.CharField(max_length=100)
    prenom = forms.CharField(max_length=100, label="Prénom")
    date_naissance = forms.DateField(widget=forms.DateInput(attrs={"type": "date"}), label="Date de naissance")
    telephone = forms.CharField(max_length=30, label="Téléphone")
    email = forms.EmailField(label="E-mail")
    filiere = forms.ModelChoiceField(queryset=Filiere.objects.all(), label="Filière")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for tp in TypePiece.objects.all():
            suffixe = " (obligatoire)" if tp.obligatoire else ""
            self.fields[f"piece_{tp.id}"] = forms.FileField(
                required=False, label=tp.libelle + suffixe, validators=[valider_fichier]
            )