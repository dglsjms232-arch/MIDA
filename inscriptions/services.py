from django.db.models import Sum

from academique.models import Dette, ReleveNotes
from paiements.models import Justificatif, Tarif


def tarif_reprise(annee, niveau):
    """Montant d'une matière à reprendre, ou None si aucun tarif n'est renseigné."""
    base = Tarif.objects.filter(type=Tarif.Type.MATIERE_REPRISE, annee=annee)
    t = base.filter(niveau=niveau).first() or base.filter(niveau__isnull=True).first()
    return t.montant if t else None


def dernier_releve(etudiant):
    return ReleveNotes.objects.filter(etudiant=etudiant).order_by("-date_saisie").first()


def dettes_examinees(ins):
    releve = dernier_releve(ins.etudiant)
    if releve is None:
        return Dette.objects.none()
    return Dette.objects.filter(
        etudiant=ins.etudiant, annee_origine=releve.annee
    ).select_related("matiere")


def situation_reprise(ins):
    """Situation pédagogique et financière d'une réinscription."""
    decision = ins.decisions_reprise.first()
    retenues = Dette.objects.filter(
        etudiant=ins.etudiant, statut=Dette.Statut.RETENUE
    ).select_related("matiere")
    tarif = tarif_reprise(ins.annee, ins.niveau)
    total = tarif * retenues.count() if tarif is not None else None
    justificatifs = Justificatif.objects.filter(
        etudiant=ins.etudiant, objet=Justificatif.Objet.MATIERE_REPRISE
    ).order_by("-date_depot")
    if decision:
        justificatifs = justificatifs.filter(date_depot__gte=decision.date)
    paye = (
        justificatifs.filter(statut=Justificatif.Statut.ACCEPTE)
        .aggregate(s=Sum("montant_declare"))["s"] or 0
    )
    reste = max(total - paye, 0) if total is not None else None
    return {
        "decision": decision, "retenues": retenues, "tarif": tarif,
        "total": total, "paye": paye, "reste": reste, "justificatifs": justificatifs,
    }


def blocages_finalisation(dettes, sit):
    """Raisons pour lesquelles la réinscription ne peut pas être finalisée."""
    raisons = []
    if dettes.filter(statut=Dette.Statut.NON_VALIDEE).exists():
        raisons.append("La décision pédagogique sur les matières non validées n'est pas prise.")
    if sit["retenues"].exists() and (sit["reste"] is None or sit["reste"] > 0):
        raisons.append("Le paiement des matières retenues n'est pas entièrement validé.")
    return raisons