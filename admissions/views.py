from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.db.models import Q
from django.http import FileResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from academique.models import AnneeAcademique
from comptes.models import Etudiant
from comptes.permissions import a_role, role_requis
from historique.models import JournalAction

from .forms import CommunicationForm, DecisionForm, DemandeForm
from .models import DecisionAdmission, Demande, PieceJointe, TypePiece

ROLES_CONSULTATION = ("Admissions", "Scolarité", "Administrateur")
ROLES_DECISION = ("Admissions", "Administrateur")


def pieces_manquantes(demande):
    fournies = demande.pieces.values_list("type_piece_id", flat=True)
    return TypePiece.objects.filter(obligatoire=True).exclude(id__in=fournies)


@login_required
def accueil(request):
    return render(request, "accueil.html", {
        "est_agent": a_role(request.user, *ROLES_CONSULTATION),
        "est_paiements": a_role(request.user, "Agent paiements", "Scolarité", "Administrateur"),
        "est_scolarite": a_role(request.user, "Scolarité", "Administrateur"),
        "est_academique": a_role(
            request.user, "Scolarité", "Responsable pédagogique", "Administrateur"
        ),
    })

@login_required
def nouvelle_demande(request):
    annee = AnneeAcademique.objects.filter(active=True).first()
    if annee is None:
        messages.error(request, "Aucune année académique active.")
        return redirect("accueil")

    form = DemandeForm(request.POST or None, request.FILES or None)
    if request.method == "POST" and form.is_valid():
        d = form.cleaned_data
        etudiant = getattr(request.user, "etudiant", None) or Etudiant(user=request.user)
        etudiant.nom = d["nom"]
        etudiant.prenom = d["prenom"]
        etudiant.date_naissance = d["date_naissance"]
        etudiant.telephone = d["telephone"]
        etudiant.email = d["email"]
        with transaction.atomic():
            etudiant.save()
            demande = Demande.objects.create(
                etudiant=etudiant, annee=annee, filiere=d["filiere"],
                mode_depot=Demande.Mode.NUMERIQUE, statut=Demande.Statut.SOUMISE,
            )
            incomplete = False
            for tp in TypePiece.objects.all():
                fichier = d.get(f"piece_{tp.id}")
                if fichier:
                    PieceJointe.objects.create(demande=demande, type_piece=tp, fichier=fichier)
                elif tp.obligatoire:
                    incomplete = True
            if incomplete:
                demande.statut = Demande.Statut.INCOMPLETE
                demande.save()
            JournalAction.objects.create(
                auteur=request.user, action="Création de la demande", objet=f"Demande {demande.id}"
            )
        messages.success(request, f"Demande n°{demande.id} enregistrée : {demande.get_statut_display()}.")
        return redirect("mes_demandes")
    return render(request, "nouvelle_demande.html", {"form": form})


@login_required
def mes_demandes(request):
    demandes = Demande.objects.filter(etudiant__user=request.user).order_by("-date_creation")
    return render(request, "mes_demandes.html", {"demandes": demandes})


@role_requis(*ROLES_CONSULTATION)
def liste_demandes(request):
    demandes = Demande.objects.select_related("etudiant", "filiere").order_by("-date_creation")
    statut = request.GET.get("statut", "")
    q = request.GET.get("q", "").strip()
    if statut:
        demandes = demandes.filter(statut=statut)
    if q:
        demandes = demandes.filter(Q(etudiant__nom__icontains=q) | Q(etudiant__prenom__icontains=q))
    return render(request, "liste_demandes.html", {
        "demandes": demandes, "statuts": Demande.Statut.choices, "statut": statut, "q": q,
    })


@role_requis(*ROLES_CONSULTATION)
def detail_demande(request, pk):
    demande = get_object_or_404(Demande.objects.select_related("etudiant", "filiere"), pk=pk)
    return render(request, "detail_demande.html", {
        "demande": demande,
        "pieces": demande.pieces.select_related("type_piece"),
        "manquantes": pieces_manquantes(demande),
        "decisions": demande.decisions.select_related("auteur").order_by("-date"),
        "communications": demande.communications.select_related("auteur").order_by("-date"),
        "historique": JournalAction.objects.filter(objet=f"Demande {demande.id}").select_related("auteur"),
        "form_decision": DecisionForm(),
        "form_comm": CommunicationForm(),
        "peut_decider": a_role(request.user, *ROLES_DECISION),
    })


@role_requis(*ROLES_DECISION)
@require_POST
def decider(request, pk):
    demande = get_object_or_404(Demande, pk=pk)
    form = DecisionForm(request.POST)
    if not form.is_valid():
        messages.error(request, " ".join(e for errs in form.errors.values() for e in errs))
        return redirect("detail_demande", pk=pk)
    resultat = form.cleaned_data["resultat"]
    motif = form.cleaned_data["motif"].strip()
    # Hypothèse à faire valider : on n'admet pas un dossier dont il manque des pièces obligatoires.
    if resultat == "admis" and pieces_manquantes(demande).exists():
        messages.error(request, "Admission impossible : des pièces obligatoires manquent.")
        return redirect("detail_demande", pk=pk)
    with transaction.atomic():
        DecisionAdmission.objects.create(
            demande=demande, resultat=resultat, auteur=request.user, motif=motif
        )
        demande.statut = Demande.Statut.ADMISE if resultat == "admis" else Demande.Statut.REFUSEE
        demande.save()
        JournalAction.objects.create(
            auteur=request.user, action=f"Décision d'admission : {resultat}",
            objet=f"Demande {demande.id}", motif=motif,
        )
    messages.success(request, "Décision enregistrée.")
    return redirect("detail_demande", pk=pk)


@role_requis(*ROLES_DECISION)
@require_POST
def enregistrer_communication(request, pk):
    demande = get_object_or_404(Demande, pk=pk)
    form = CommunicationForm(request.POST)
    if form.is_valid():
        with transaction.atomic():
            c = form.save(commit=False)
            c.demande = demande
            c.auteur = request.user
            c.save()
            JournalAction.objects.create(
                auteur=request.user, action="Communication du résultat",
                objet=f"Demande {demande.id}", motif=c.resume,
            )
        messages.success(request, "Communication enregistrée.")
    else:
        messages.error(request, "Le canal et le résumé sont obligatoires.")
    return redirect("detail_demande", pk=pk)


@login_required
def piece_fichier(request, pk):
    """Les pièces ne sont pas publiques : seul le propriétaire ou un agent habilité y accède."""
    piece = get_object_or_404(PieceJointe.objects.select_related("demande__etudiant"), pk=pk)
    proprietaire = piece.demande.etudiant.user_id == request.user.id
    if not (proprietaire or a_role(request.user, *ROLES_CONSULTATION)):
        raise PermissionDenied
    return FileResponse(piece.fichier.open("rb"))