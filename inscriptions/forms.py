from django import forms

from academique.models import Dette, Niveau


class FinalisationForm(forms.Form):
    niveau = forms.ModelChoiceField(queryset=Niveau.objects.none(), label="Niveau d'inscription")

    def __init__(self, *args, filiere=None, **kwargs):
        super().__init__(*args, **kwargs)
        if filiere is not None:
            self.fields["niveau"].queryset = Niveau.objects.filter(filiere=filiere)


class DecisionRepriseForm(forms.Form):
    dettes = forms.ModelMultipleChoiceField(
        queryset=Dette.objects.none(),
        widget=forms.CheckboxSelectMultiple,
        required=False,
        label="Matières à reprendre",
    )
    motif = forms.CharField(widget=forms.Textarea(attrs={"rows": 3}), label="Justification de la décision")

    def __init__(self, *args, dettes_qs=None, **kwargs):
        super().__init__(*args, **kwargs)
        if dettes_qs is not None:
            self.fields["dettes"].queryset = dettes_qs.select_related("matiere")
        self.fields["dettes"].label_from_instance = lambda d: f"{d.matiere.code} - {d.matiere.intitule}"