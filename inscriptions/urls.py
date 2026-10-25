from django.urls import path

from . import views

urlpatterns = [
    path("a-finaliser/", views.a_finaliser, name="a_finaliser"),
    path("finaliser/<int:pk>/", views.finaliser, name="finaliser"),
    path("fiche/<int:pk>/", views.fiche_inscription, name="fiche_inscription"),
]