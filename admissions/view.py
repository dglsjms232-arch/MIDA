@login_required
def accueil(request):
    return render(request, "accueil.html", {
        "est_agent": a_role(request.user, *ROLES_CONSULTATION),
        "est_paiements": a_role(request.user, "Agent paiements", "Scolarité", "Administrateur"),
        "est_scolarite": a_role(request.user, "Scolarité", "Administrateur"),
        "est_academique": a_role(
            request.user, "Scolarité", "Responsable pédagogique", "Administrateur"
        ),
        "est_suivi": a_role(
            request.user, "Admissions", "Scolarité", "Agent paiements",
            "Responsable pédagogique", "Administrateur",
        ),
    })