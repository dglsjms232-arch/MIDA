from functools import wraps

from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied


def a_role(user, *roles):
    return user.is_authenticated and (
        user.is_superuser or user.groups.filter(name__in=roles).exists()
    )


def role_requis(*roles):
    def decorateur(vue):
        @wraps(vue)
        @login_required
        def enveloppe(request, *args, **kwargs):
            if not a_role(request.user, *roles):
                raise PermissionDenied
            return vue(request, *args, **kwargs)
        return enveloppe
    return decorateur