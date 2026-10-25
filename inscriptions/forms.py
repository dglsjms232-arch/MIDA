from django import forms

from academique.models import Niveau


class FinalisationForm(forms.Form):
    niveau = forms.ModelChoiceField(queryset=Niveau.objects.none(), label="Niveau d'inscription")

    def __init__(self, *args, filiere=None, **kwargs):
        super().__init__(*args, **kwargs)
        if filiere is not None:
            self.fields["niveau"].queryset = Niveau.objects.filter(filiere=filiere)