from django.db.models import Q
from django.shortcuts import get_object_or_404, render

from academique.models import Dette, ReleveNotes
from admissions.models import Demande
from comptes.models import Etudiant
from comptes.permissions import role_requis
from inscriptions.models import Inscription
from paiements.models import Justificatif

from .models import JournalAction

ROLES_SUIVI = (
    "Admissions", "Scolarité", "Agent paiements",
    "Responsable pédagogique", "Administrateur",
)


@role_requis(*ROLES_SUIVI)
def suivi(request):
    return render(request, "suivi.html", {
        "en_attente": Demande.objects.filter(
            statut__in=[Demande.Statut.SOUMISE, Demande.Statut.EN_ETUDE]
        ).select_related("etudiant", "filiere").order_by("-date_creation"),
        "incompletes": Demande.objects.filter(
            statut=Demande.Statut.INCOMPLETE
        ).select_related("etudiant", "filiere").order_by("-date_creation"),
        "justificatifs": Justificatif.objects.filter(
            statut=Justificatif.Statut.EN_ATTENTE
        ).select_related("etudiant").order_by("-date_depot"),
        "finalisees": Inscription.objects.filter(
            statut=Inscription.Statut.FINALISEE
        ).select_related("etudiant", "annee", "niveau").order_by("-date_finalisation"),
        # Hypothèse : une dette reste à régulariser tant qu'elle est non validée ou retenue.
        "dettes": Dette.objects.filter(
            statut__in=[Dette.Statut.NON_VALIDEE, Dette.Statut.RETENUE]
        ).select_related("etudiant", "matiere").order_by("etudiant__nom"),
    })


@role_requis(*ROLES_SUIVI)
def recherche_dossier(request):
    q = request.GET.get("q", "").strip()
    etudiants = Etudiant.objects.none()
    if q:
        etudiants = Etudiant.objects.filter(
            Q(nom__icontains=q) | Q(prenom__icontains=q) | Q(matricule__icontains=q)
        ).order_by("nom")
    return render(request, "recherche_dossier.html", {"etudiants": etudiants, "q": q})


@role_requis(*ROLES_SUIVI)
def dossier_etudiant(request, pk):
    etudiant = get_object_or_404(Etudiant, pk=pk)
    demandes = Demande.objects.filter(etudiant=etudiant).select_related("filiere")
    inscriptions = Inscription.objects.filter(etudiant=etudiant).select_related("annee", "niveau")
    justificatifs = Justificatif.objects.filter(etudiant=etudiant).order_by("-date_depot")
    releves = ReleveNotes.objects.filter(etudiant=etudiant).select_related("annee")
    dettes = Dette.objects.filter(etudiant=etudiant).select_related("matiere", "annee_origine")

    objets = (
        [f"Demande {d.id}" for d in demandes]
        + [f"Justificatif {j.id}" for j in justificatifs]
        + [f"Relevé {r.id}" for r in releves]
        + [f"Réinscription {i.id}" for i in inscriptions]
    )
    historique = JournalAction.objects.filter(objet__in=objets).select_related("auteur")
    return render(request, "dossier_etudiant.html", {
        "etudiant": etudiant, "demandes": demandes, "inscriptions": inscriptions,
        "justificatifs": justificatifs, "releves": releves, "dettes": dettes,
        "historique": historique,
    })