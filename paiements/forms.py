from django import forms

from admissions.forms import valider_fichier

from .models import Justificatif


class JustificatifForm(forms.ModelForm):
    fichier = forms.FileField(validators=[valider_fichier], label="Reçu bancaire (PDF, JPG, PNG)")

    class Meta:
        model = Justificatif
        fields = ["fichier", "montant_declare", "reference_bancaire"]
        labels = {
            "montant_declare": "Montant versé",
            "reference_bancaire": "Référence du reçu bancaire",
        }


class ControleForm(forms.Form):
    resultat = forms.ChoiceField(
        choices=[("accepte", "Accepter"), ("refuse", "Refuser")], label="Décision"
    )
    motif = forms.CharField(widget=forms.Textarea(attrs={"rows": 3}), required=False)

    def clean(self):
        d = super().clean()
        if d.get("resultat") == "refuse" and not (d.get("motif") or "").strip():
            self.add_error("motif", "Un motif est obligatoire pour un refus.")
        return d