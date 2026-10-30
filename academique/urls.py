from django.urls import path

from . import views

urlpatterns = [
    path("releves/", views.liste_releves, name="liste_releves"),
    path("releves/<int:pk>/", views.detail_releve, name="detail_releve"),
    path("releves/importer/", views.import_releve, name="import_releve"),
]