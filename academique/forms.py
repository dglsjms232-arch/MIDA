import os

from django import forms

from comptes.models import Etudiant

from .models import AnneeAcademique, Niveau


class ImportReleveForm(forms.Form):
    etudiant = forms.ModelChoiceField(queryset=Etudiant.objects.order_by("nom", "prenom"), label="Étudiant")
    annee = forms.ModelChoiceField(queryset=AnneeAcademique.objects.all(), label="Année examinée")
    niveau = forms.ModelChoiceField(queryset=Niveau.objects.select_related("filiere"), label="Niveau de l'année examinée")
    fichier = forms.FileField(label="Fichier CSV des résultats validés")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["etudiant"].label_from_instance = (
            lambda e: f"{e.nom} {e.prenom} ({e.matricule or 'sans matricule'})"
        )

    def clean_fichier(self):
        f = self.cleaned_data["fichier"]
        if os.path.splitext(f.name)[1].lower() != ".csv":
            raise forms.ValidationError("Le fichier doit être au format CSV.")
        if f.size > 1024 * 1024:
            raise forms.ValidationError("Fichier trop volumineux (1 Mo maximum).")
        return f