from paiements.models import Tarif


def tarif_reprise(annee, niveau):
    """Montant d'une matière à reprendre, ou None si aucun tarif n'est renseigné."""
    base = Tarif.objects.filter(type=Tarif.Type.MATIERE_REPRISE, annee=annee)
    t = base.filter(niveau=niveau).first() or base.filter(niveau__isnull=True).first()
    return t.montant if t else None