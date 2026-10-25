from django.urls import path

from . import views

urlpatterns = [
    path("", views.accueil, name="accueil"),
    path("demande/nouvelle/", views.nouvelle_demande, name="nouvelle_demande"),
    path("demande/mes-demandes/", views.mes_demandes, name="mes_demandes"),
]