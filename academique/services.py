from .models import Dette


def creer_dettes(releve):
    """Crée une dette pour chaque matière non validée du relevé (sans doublon)."""
    for ligne in releve.lignes.filter(validee=False).select_related("matiere"):
        Dette.objects.get_or_create(
            etudiant=releve.etudiant,
            matiere=ligne.matiere,
            annee_origine=releve.annee,
            defaults={"statut": Dette.Statut.NON_VALIDEE},
        )