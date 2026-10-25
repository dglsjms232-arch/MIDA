from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.shortcuts import redirect, render

from academique.models import AnneeAcademique
from comptes.models import Etudiant
from historique.models import JournalAction

from .forms import DemandeForm
from .models import Demande, PieceJointe, TypePiece


@login_required
def accueil(request):
    return render(request, "accueil.html")


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