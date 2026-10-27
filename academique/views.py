from django.shortcuts import get_object_or_404, render

from comptes.permissions import role_requis

from .models import Dette, ReleveNotes

ROLES_ACADEMIQUE = ("Scolarité", "Responsable pédagogique", "Administrateur")

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
    return render(request, "liste_releves.html", {"releves": releves})


@role_requis(*ROLES_ACADEMIQUE)
def detail_releve(request, pk):
    releve = get_object_or_404(
        ReleveNotes.objects.select_related("etudiant", "annee", "niveau"), pk=pk
    )
    return render(request, "detail_releve.html", {
        "releve": releve,
        "lignes": releve.lignes.select_related("matiere").order_by("matiere__code"),
        "dettes": Dette.objects.filter(
            etudiant=releve.etudiant, annee_origine=releve.annee
        ).select_related("matiere"),
        "message_situation": SITUATIONS[releve.situation],
    })