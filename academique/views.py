from django.contrib import messages
from django.core.exceptions import ValidationError
from django.shortcuts import get_object_or_404, redirect, render

from comptes.permissions import a_role, role_requis
from inscriptions.models import Inscription

from . import services
from .forms import ImportReleveForm
from .models import Dette, ReleveNotes

ROLES_ACADEMIQUE = ("Scolarité", "Responsable pédagogique", "Administrateur")
ROLES_IMPORT = ("Scolarité", "Administrateur")

SITUATIONS = {
    "complet": (
        "60 crédits obtenus : aucune dette issue de l'année examinée. "
        "Une éventuelle dette antérieure n'est pas exclue (traitement à préciser)."
    ),
    "reinscription": (
        "Entre 40 et 59 crédits : la procédure de réinscription peut être engagée. "
        "Les matières non validées doivent être examinées par le responsable pédagogique."
    ),
    "decision_institutionnelle": (
        "Moins de 40 crédits : pas de passage automatique. "
        "Le dossier doit être orienté vers une décision institutionnelle (règle à préciser)."
    ),
}


@role_requis(*ROLES_ACADEMIQUE)
def liste_releves(request):
    releves = ReleveNotes.objects.select_related("etudiant", "annee", "niveau").order_by(
        "etudiant__nom"
    )
    return render(request, "liste_releves.html", {
        "releves": releves,
        "peut_importer": a_role(request.user, *ROLES_IMPORT),
    })


@role_requis(*ROLES_ACADEMIQUE)
def detail_releve(request, pk):
    releve = get_object_or_404(
        ReleveNotes.objects.select_related("etudiant", "annee", "niveau"), pk=pk
    )
    inscription = Inscription.objects.filter(
        etudiant=releve.etudiant, type=Inscription.Type.REINSCRIPTION, annee__active=True
    ).first()
    return render(request, "detail_releve.html", {
        "releve": releve,
        "lignes": releve.lignes.select_related("matiere").order_by("matiere__code"),
        "dettes": Dette.objects.filter(
            etudiant=releve.etudiant, annee_origine=releve.annee
        ).select_related("matiere"),
        "message_situation": SITUATIONS[releve.situation],
        "inscription": inscription,
        "peut_ouvrir": a_role(request.user, "Scolarité", "Administrateur"),
    })


@role_requis(*ROLES_IMPORT)
def import_releve(request):
    form = ImportReleveForm(request.POST or None, request.FILES or None)
    if request.method == "POST" and form.is_valid():
        d = form.cleaned_data
        try:
            releve = services.importer_releve(
                d["etudiant"], d["annee"], d["niveau"], d["fichier"], request.user
            )
        except ValidationError as e:
            for m in e.messages:
                messages.error(request, m)
        else:
            messages.success(request, f"Relevé importé : {releve.credits_obtenus} crédits obtenus.")
            return redirect("detail_releve", pk=releve.pk)
    return render(request, "importer_releve.html", {"form": form})