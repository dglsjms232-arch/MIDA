from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.http import FileResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from admissions.models import Demande
from comptes.permissions import a_role, role_requis
from historique.models import JournalAction
from inscriptions.models import Inscription
from inscriptions.services import situation_reprise
from .forms import ControleForm, JustificatifForm
from .models import Justificatif

ROLES_CONTROLE = ("Agent paiements", "Administrateur")
ROLES_LECTURE = ("Agent paiements", "Scolarité", "Administrateur")


@login_required
def mes_justificatifs(request):
    etudiant = getattr(request.user, "etudiant", None)
    if etudiant is None:
        justificatifs = Justificatif.objects.none()
        inscriptions = Inscription.objects.none()
        admise = False
    else:
        justificatifs = Justificatif.objects.filter(etudiant=etudiant).order_by("-date_depot")
        inscriptions = Inscription.objects.filter(
            etudiant=etudiant, statut=Inscription.Statut.FINALISEE
        )
        admise = Demande.objects.filter(etudiant=etudiant, statut=Demande.Statut.ADMISE).exists()

    bloque = justificatifs.filter(
        objet=Justificatif.Objet.PREMIERE_TRANCHE,
        statut__in=[Justificatif.Statut.EN_ATTENTE, Justificatif.Statut.ACCEPTE],
    ).exists()
    peut_deposer = admise and not bloque

    reprise = None
    peut_deposer_reprise = False
    if etudiant is not None:
        ins_r = Inscription.objects.filter(
            etudiant=etudiant, type=Inscription.Type.REINSCRIPTION,
            statut=Inscription.Statut.EN_COURS,
        ).first()
        if ins_r:
            sit = situation_reprise(ins_r)
            if sit["retenues"].exists():
                reprise = sit
                en_attente = sit["justificatifs"].filter(statut=Justificatif.Statut.EN_ATTENTE).exists()
                peut_deposer_reprise = bool(sit["reste"]) and not en_attente

    form = JustificatifForm()
    form_reprise = JustificatifForm()
    if request.method == "POST":
        if request.POST.get("objet") == "matiere_reprise":
            if not peut_deposer_reprise:
                raise PermissionDenied
            form_reprise = JustificatifForm(request.POST, request.FILES)
            cible = form_reprise
            objet = Justificatif.Objet.MATIERE_REPRISE
            action = "Dépôt du justificatif de paiement des matières à reprendre"
        else:
            if not peut_deposer:
                raise PermissionDenied
            form = JustificatifForm(request.POST, request.FILES)
            cible = form
            objet = Justificatif.Objet.PREMIERE_TRANCHE
            action = "Dépôt du justificatif de première tranche"
        if cible.is_valid():
            with transaction.atomic():
                j = cible.save(commit=False)
                j.etudiant = etudiant
                j.objet = objet
                j.save()
                JournalAction.objects.create(
                    auteur=request.user, action=action, objet=f"Justificatif {j.id}"
                )
            messages.success(request, "Justificatif envoyé : il sera contrôlé par un agent habilité.")
            return redirect("mes_justificatifs")

    return render(request, "mes_justificatifs.html", {
        "justificatifs": justificatifs,
        "inscriptions": inscriptions,
        "admise": admise,
        "bloque": bloque,
        "peut_deposer": peut_deposer,
        "form": form,
        "reprise": reprise,
        "peut_deposer_reprise": peut_deposer_reprise,
        "form_reprise": form_reprise,
    })


@role_requis(*ROLES_LECTURE)
def liste_controle(request):
    statut = request.GET.get("statut", "en_attente")
    justificatifs = Justificatif.objects.select_related("etudiant").order_by("-date_depot")
    if statut:
        justificatifs = justificatifs.filter(statut=statut)
    return render(request, "liste_controle.html", {
        "justificatifs": justificatifs,
        "statuts": Justificatif.Statut.choices,
        "statut": statut,
    })


@role_requis(*ROLES_LECTURE)
def detail_justificatif(request, pk):
    j = get_object_or_404(Justificatif.objects.select_related("etudiant", "verifie_par"), pk=pk)
    return render(request, "detail_justificatif.html", {
        "j": j,
        "form": ControleForm(),
        "peut_controler": a_role(request.user, *ROLES_CONTROLE)
        and j.statut == Justificatif.Statut.EN_ATTENTE,
        "historique": JournalAction.objects.filter(objet=f"Justificatif {j.id}").select_related("auteur"),
    })


@role_requis(*ROLES_CONTROLE)
@require_POST
def controler(request, pk):
    j = get_object_or_404(Justificatif, pk=pk)
    if j.statut != Justificatif.Statut.EN_ATTENTE:
        messages.error(request, "Ce justificatif a déjà été traité.")
        return redirect("detail_justificatif", pk=pk)
    form = ControleForm(request.POST)
    if not form.is_valid():
        messages.error(request, " ".join(e for errs in form.errors.values() for e in errs))
        return redirect("detail_justificatif", pk=pk)
    resultat = form.cleaned_data["resultat"]
    motif = form.cleaned_data["motif"].strip()
    with transaction.atomic():
        j.statut = resultat
        j.motif_refus = motif if resultat == "refuse" else ""
        j.verifie_par = request.user
        j.date_verification = timezone.now()
        j.save()
        JournalAction.objects.create(
            auteur=request.user,
            action=f"Contrôle du justificatif : {resultat}",
            objet=f"Justificatif {j.id}",
            motif=motif,
        )
    messages.success(request, "Décision enregistrée.")
    return redirect("detail_justificatif", pk=pk)


@login_required
def justificatif_fichier(request, pk):
    j = get_object_or_404(Justificatif.objects.select_related("etudiant"), pk=pk)
    proprietaire = j.etudiant.user_id == request.user.id
    if not (proprietaire or a_role(request.user, *ROLES_LECTURE)):
        raise PermissionDenied
    return FileResponse(j.fichier.open("rb"))