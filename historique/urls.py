from django.urls import path

from . import views

urlpatterns = [
    path("suivi/", views.suivi, name="suivi"),
    path("etudiants/", views.recherche_dossier, name="recherche_dossier"),
    path("etudiants/<int:pk>/", views.dossier_etudiant, name="dossier_etudiant"),
]