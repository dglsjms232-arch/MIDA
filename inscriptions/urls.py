from django.urls import path

from . import views

urlpatterns = [
    path("a-finaliser/", views.a_finaliser, name="a_finaliser"),
    path("finaliser/<int:pk>/", views.finaliser, name="finaliser"),
    path("fiche/<int:pk>/", views.fiche_inscription, name="fiche_inscription"),
    path("reinscription/ouvrir/<int:releve_pk>/", views.ouvrir_reinscription, name="ouvrir_reinscription"),
    path("reinscription/<int:pk>/", views.detail_reinscription, name="detail_reinscription"),
    path("reinscription/<int:pk>/decision/", views.decider_reprise, name="decider_reprise"),
]