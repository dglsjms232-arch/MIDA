from django.contrib import admin
from django.contrib.auth import views as auth_views
from django.urls import include, path

urlpatterns = [
    path("admin/", admin.site.urls),
    path("connexion/", auth_views.LoginView.as_view(template_name="connexion.html"), name="connexion"),
    path("deconnexion/", auth_views.LogoutView.as_view(), name="deconnexion"),
    path("paiements/", include("paiements.urls")),
    path("inscriptions/", include("inscriptions.urls")),
    path("academique/", include("academique.urls")),
    path("", include("admissions.urls")),
]