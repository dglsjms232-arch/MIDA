from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from admissions.models import Demande
from comptes.permissions import a_role, role_requis
from historique.models import JournalAction
from paiements.models import Justificatif

from .forms import FinalisationForm
from .models import Inscription

ROLES_SCOLARITE = ("Scolarité", "Administrateur")


def justificatif_accepte(etudiant):
    return Justificatif.objects.filter(
        etudiant=etudiant,
        objet=Justificatif.Objet.PREMIERE_TRANCHE,
        statut=Justificatif.Statut.ACCEPTE,
    ).first()


def inscription_existante(demande):
    return Inscription.objects.filter(
        etudiant=demande.etudiant, annee=demande.annee, type=Inscription.Type.NOUVELLE
    ).first()


@role_requis(*ROLES_SCOLARITE)
def a_finaliser(request):
    demandes = (
        Demande.objects.filter(statut=Demande.Statut.ADMISE)
        .select_related("etudiant", "filiere")
        .order_by("-date_creation")
    )
    lignes = [
        {
            "demande": d,
            "paiement_ok": justificatif_accepte(d.etudiant) is not None,
            "inscription": inscription_existante(d),
        }
        for d in demandes
    ]
    return render(request, "a_finaliser.html", {"lignes": lignes})


@role_requis(*ROLES_SCOLARITE)
def finaliser(request, pk):
    demande = get_object_or_404(
        Demande.objects.select_related("etudiant", "filiere", "annee"), pk=pk
    )
    deja = inscription_existante(demande)
    paiement_ok = justificatif_accepte(demande.etudiant) is not None
    form = FinalisationForm(request.POST or None, filiere=demande.filiere)

    if request.method == "POST":
        if deja:
            messages.error(request, "Cette inscription est déjà finalisée.")
        elif demande.statut != Demande.Statut.ADMISE:
            messages.error(request, "Le candidat n'est pas admis.")
        elif not paiement_ok:
            messages.error(request, "Finalisation impossible : le justificatif de première tranche n'est pas accepté.")
        elif form.is_valid():
            with transaction.atomic():
                ins = Inscription.objects.create(
                    etudiant=demande.etudiant,
                    annee=demande.annee,
                    niveau=form.cleaned_data["niveau"],
                    type=Inscription.Type.NOUVELLE,
                    statut=Inscription.Statut.FINALISEE,
                    finalisee_par=request.user,
                    date_finalisation=timezone.now(),
                )
                etudiant = demande.etudiant
                if not etudiant.matricule:
                    # Hypothèse : format de matricule provisoire, à faire valider.
                    etudiant.matricule = f"UCAO-{demande.annee.libelle[:4]}-{etudiant.id:04d}"
                    etudiant.save()
                JournalAction.objects.create(
                    auteur=request.user,
                    action="Inscription définitive finalisée",
                    objet=f"Demande {demande.id}",
                )
            messages.success(request, "Inscription finalisée.")
            return redirect("fiche_inscription", pk=ins.pk)

    return render(request, "finaliser.html", {
        "demande": demande, "form": form, "paiement_ok": paiement_ok, "deja": deja,
    })


@login_required
def fiche_inscription(request, pk):
    ins = get_object_or_404(
        Inscription.objects.select_related(
            "etudiant", "annee", "niveau", "niveau__filiere", "finalisee_par"
        ),
        pk=pk,
    )
    proprietaire = ins.etudiant.user_id == request.user.id
    if not (proprietaire or a_role(request.user, *ROLES_SCOLARITE)):
        raise PermissionDenied
    return render(request, "fiche_inscription.html", {
        "ins": ins,
        "justificatif": justificatif_accepte(ins.etudiant),
    })