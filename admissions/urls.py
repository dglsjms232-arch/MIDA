from django.urls import path

from . import views

urlpatterns = [
    path("", views.accueil, name="accueil"),
    path("demande/nouvelle/", views.nouvelle_demande, name="nouvelle_demande"),
    path("demande/mes-demandes/", views.mes_demandes, name="mes_demandes"),
    path("dossiers/", views.liste_demandes, name="liste_demandes"),
    path("dossiers/<int:pk>/", views.detail_demande, name="detail_demande"),
    path("dossiers/<int:pk>/decision/", views.decider, name="decider"),
    path("dossiers/<int:pk>/communication/", views.enregistrer_communication, name="enregistrer_communication"),
    path("pieces/<int:pk>/", views.piece_fichier, name="piece_fichier"),
]