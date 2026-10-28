from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from academique.models import AnneeAcademique, Dette, Niveau, ReleveNotes
from academique.views import SITUATIONS
from admissions.models import Demande
from comptes.permissions import a_role, role_requis
from historique.models import JournalAction
from paiements.models import Justificatif

from .forms import DecisionRepriseForm, FinalisationForm
from .models import DecisionReprise, Inscription, MatiereReprise
from .services import blocages_finalisation, dernier_releve, dettes_examinees, situation_reprise

ROLES_SCOLARITE = ("Scolarité", "Administrateur")
ROLES_REINSCRIPTION = ("Scolarité", "Responsable pédagogique", "Administrateur")
ROLES_DECISION_REPRISE = ("Responsable pédagogique", "Administrateur")


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


# ---------- Nouvelle inscription ----------

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
        "sit": situation_reprise(ins) if ins.type == Inscription.Type.REINSCRIPTION else {},
    })

# ---------- Réinscription ----------

@role_requis(*ROLES_SCOLARITE)
@require_POST
def ouvrir_reinscription(request, releve_pk):
    releve = get_object_or_404(ReleveNotes.objects.select_related("etudiant", "niveau"), pk=releve_pk)
    annee = AnneeAcademique.objects.filter(active=True).first()
    if annee is None:
        messages.error(request, "Aucune année académique active.")
        return redirect("detail_releve", pk=releve.pk)

    if releve.situation == "decision_institutionnelle":
        JournalAction.objects.create(
            auteur=request.user,
            action="Dossier orienté vers une décision institutionnelle",
            objet=f"Relevé {releve.id}",
            motif=f"{releve.credits_obtenus} crédits obtenus, sous le seuil de 40",
        )
        messages.warning(
            request,
            "Moins de 40 crédits : aucune réinscription créée. "
            "Le dossier est orienté vers une décision institutionnelle.",
        )
        return redirect("detail_releve", pk=releve.pk)

    existante = Inscription.objects.filter(
        etudiant=releve.etudiant, annee=annee, type=Inscription.Type.REINSCRIPTION
    ).first()
    if existante:
        return redirect("detail_reinscription", pk=existante.pk)

    # Hypothèse provisoire : réinscription dans le niveau suivant de la filière.
    suivant = Niveau.objects.filter(
        filiere=releve.niveau.filiere, id__gt=releve.niveau.id
    ).order_by("id").first()
    with transaction.atomic():
        ins = Inscription.objects.create(
            etudiant=releve.etudiant,
            annee=annee,
            niveau=suivant or releve.niveau,
            type=Inscription.Type.REINSCRIPTION,
            statut=Inscription.Statut.EN_COURS,
        )
        JournalAction.objects.create(
            auteur=request.user,
            action="Réinscription engagée",
            objet=f"Réinscription {ins.id}",
            motif=f"{releve.credits_obtenus} crédits obtenus",
        )
    messages.success(request, "Réinscription engagée.")
    return redirect("detail_reinscription", pk=ins.pk)


@role_requis(*ROLES_REINSCRIPTION)
def detail_reinscription(request, pk):
    ins = get_object_or_404(
        Inscription.objects.select_related("etudiant", "annee", "niveau"),
        pk=pk, type=Inscription.Type.REINSCRIPTION,
    )
    releve = dernier_releve(ins.etudiant)
    dettes = dettes_examinees(ins)
    sit = situation_reprise(ins)
    blocages = blocages_finalisation(dettes, sit)
    en_cours = ins.statut == Inscription.Statut.EN_COURS
    peut_decider = (
        a_role(request.user, *ROLES_DECISION_REPRISE) and sit["decision"] is None
        and dettes.filter(statut=Dette.Statut.NON_VALIDEE).exists()
    )
    return render(request, "detail_reinscription.html", {
        "ins": ins,
        "releve": releve,
        "message_situation": SITUATIONS[releve.situation] if releve else "",
        "dettes": dettes,
        "sit": sit,
        "peut_decider": peut_decider,
        "peut_finaliser": a_role(request.user, *ROLES_SCOLARITE) and en_cours,
        "blocages": blocages,
        "form": DecisionRepriseForm(dettes_qs=dettes.filter(statut=Dette.Statut.NON_VALIDEE)),
        "historique": JournalAction.objects.filter(
            objet=f"Réinscription {ins.id}"
        ).select_related("auteur"),
    })


@role_requis(*ROLES_DECISION_REPRISE)
@require_POST
def decider_reprise(request, pk):
    ins = get_object_or_404(Inscription, pk=pk, type=Inscription.Type.REINSCRIPTION)
    releve = ReleveNotes.objects.filter(etudiant=ins.etudiant).order_by("-date_saisie").first()
    if releve is None or ins.decisions_reprise.exists():
        messages.error(request, "Une décision existe déjà ou aucun relevé n'est disponible.")
        return redirect("detail_reinscription", pk=pk)

    dettes = Dette.objects.filter(
        etudiant=ins.etudiant, annee_origine=releve.annee, statut=Dette.Statut.NON_VALIDEE
    )
    form = DecisionRepriseForm(request.POST, dettes_qs=dettes)
    if not form.is_valid():
        messages.error(request, "Décision refusée : la justification est obligatoire.")
        return redirect("detail_reinscription", pk=pk)

    ids = {d.id for d in form.cleaned_data["dettes"]}
    motif = form.cleaned_data["motif"].strip()
    with transaction.atomic():
        decision = DecisionReprise.objects.create(inscription=ins, responsable=request.user, motif=motif)
        for d in dettes:
            if d.id in ids:
                d.statut = Dette.Statut.RETENUE
                MatiereReprise.objects.create(decision=decision, dette=d)
            else:
                d.statut = Dette.Statut.NON_RETENUE
            d.save()
        JournalAction.objects.create(
            auteur=request.user,
            action="Décision pédagogique de reprise",
            objet=f"Réinscription {ins.id}",
            motif=f"{len(ids)} matière(s) retenue(s) : {motif}",
        )
    messages.success(request, "Décision pédagogique enregistrée.")
    return redirect("detail_reinscription", pk=pk)
@role_requis(*ROLES_SCOLARITE)
@require_POST
def finaliser_reinscription(request, pk):
    ins = get_object_or_404(Inscription, pk=pk, type=Inscription.Type.REINSCRIPTION)
    if ins.statut == Inscription.Statut.FINALISEE:
        return redirect("fiche_inscription", pk=pk)
    sit = situation_reprise(ins)
    raisons = blocages_finalisation(dettes_examinees(ins), sit)
    if raisons:
        messages.error(request, "Finalisation impossible : " + " ".join(raisons))
        return redirect("detail_reinscription", pk=pk)
    with transaction.atomic():
        ins.statut = Inscription.Statut.FINALISEE
        ins.finalisee_par = request.user
        ins.date_finalisation = timezone.now()
        ins.save()
        JournalAction.objects.create(
            auteur=request.user,
            action="Réinscription finalisée",
            objet=f"Réinscription {ins.id}",
            motif=f"{sit['retenues'].count()} matière(s) retenue(s), montant validé : {sit['paye']}",
        )
    messages.success(request, "Réinscription finalisée.")
    return redirect("fiche_inscription", pk=pk)