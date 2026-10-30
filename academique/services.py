import csv
import io
import unicodedata
from decimal import Decimal, InvalidOperation

from django.core.exceptions import ValidationError
from django.db import transaction

from historique.models import JournalAction

from .models import Dette, LigneReleve, Matiere, ReleveNotes

OUI = {"oui", "o", "1", "true", "vrai", "valide"}
NON = {"non", "n", "0", "false", "faux", "non valide"}


def _norm(texte):
    """Minuscules sans accents, pour comparer les saisies."""
    t = unicodedata.normalize("NFD", texte.strip().lower())
    return "".join(c for c in t if unicodedata.category(c) != "Mn")


def creer_dettes(releve):
    """Crée une dette pour chaque matière non validée du relevé (sans doublon)."""
    for ligne in releve.lignes.filter(validee=False).select_related("matiere"):
        Dette.objects.get_or_create(
            etudiant=releve.etudiant,
            matiere=ligne.matiere,
            annee_origine=releve.annee,
            defaults={"statut": Dette.Statut.NON_VALIDEE},
        )


def lire_lignes(fichier):
    brut = fichier.read()
    try:
        texte = brut.decode("utf-8-sig")
    except UnicodeDecodeError:
        texte = brut.decode("cp1252")
    if not texte.strip():
        raise ValidationError("Le fichier est vide.")
    delimiteur = ";" if ";" in texte.splitlines()[0] else ","
    lecteur = csv.DictReader(io.StringIO(texte), delimiter=delimiteur)
    champs = [_norm(c) for c in (lecteur.fieldnames or [])]
    if "code" not in champs or "validee" not in champs:
        raise ValidationError("Colonnes attendues : code, note, validee (séparées par ; ou ,).")
    lignes = []
    for numero, brute in enumerate(lecteur, start=2):
        ligne = {_norm(k or ""): (v or "").strip() for k, v in brute.items()}
        if any(ligne.values()):
            lignes.append((numero, ligne))
    return lignes


def importer_releve(etudiant, annee, niveau, fichier, utilisateur):
    """Importe un relevé de notes validé (aucun calcul de notes, aucune délibération)."""
    if ReleveNotes.objects.filter(etudiant=etudiant, annee=annee).exists():
        raise ValidationError("Un relevé existe déjà pour cet étudiant et cette année.")
    lignes = lire_lignes(fichier)
    if not lignes:
        raise ValidationError("Aucune ligne de résultat dans le fichier.")

    matieres = {m.code.upper(): m for m in Matiere.objects.all()}
    erreurs, vus, donnees = [], set(), []
    for numero, l in lignes:
        code = l.get("code", "").upper()
        matiere = matieres.get(code)
        if matiere is None:
            erreurs.append(f"Ligne {numero} : matière inconnue « {code} ».")
            continue
        if code in vus:
            erreurs.append(f"Ligne {numero} : matière « {code} » en double.")
            continue
        vus.add(code)
        v = _norm(l.get("validee", ""))
        if v in OUI:
            validee = True
        elif v in NON:
            validee = False
        else:
            erreurs.append(f"Ligne {numero} : la colonne validee doit valoir oui ou non.")
            continue
        note = None
        if l.get("note"):
            try:
                note = Decimal(l["note"].replace(",", "."))
            except InvalidOperation:
                erreurs.append(f"Ligne {numero} : note incorrecte « {l['note']} ».")
                continue
            if not 0 <= note <= 20:
                erreurs.append(f"Ligne {numero} : la note doit être comprise entre 0 et 20.")
                continue
        donnees.append((matiere, note, validee))
    if erreurs:
        raise ValidationError(erreurs[:10])

    credits = sum(m.credits for m, _, v in donnees if v)
    if credits > 60:
        raise ValidationError(f"Le total des crédits validés ({credits}) dépasse 60.")

    with transaction.atomic():
        releve = ReleveNotes.objects.create(
            etudiant=etudiant, annee=annee, niveau=niveau,
            credits_obtenus=credits, saisi_par=utilisateur,
        )
        LigneReleve.objects.bulk_create(
            [LigneReleve(releve=releve, matiere=m, note=n, validee=v) for m, n, v in donnees]
        )
        creer_dettes(releve)
        JournalAction.objects.create(
            auteur=utilisateur,
            action="Import d'un relevé de notes",
            objet=f"Relevé {releve.id}",
            motif=f"{credits} crédits obtenus, {sum(1 for _, _, v in donnees if not v)} matière(s) non validée(s)",
        )
    return releve