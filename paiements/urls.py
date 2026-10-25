from django.urls import path

from . import views

urlpatterns = [
    path("mes-justificatifs/", views.mes_justificatifs, name="mes_justificatifs"),
    path("controle/", views.liste_controle, name="liste_controle"),
    path("controle/<int:pk>/", views.detail_justificatif, name="detail_justificatif"),
    path("controle/<int:pk>/decision/", views.controler, name="controler"),
    path("fichier/<int:pk>/", views.justificatif_fichier, name="justificatif_fichier"),
]