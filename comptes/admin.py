from django.apps import apps
from django.contrib import admin

for modele in apps.get_app_config("comptes").get_models():
    admin.site.register(modele)