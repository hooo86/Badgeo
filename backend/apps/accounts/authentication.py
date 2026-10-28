from rest_framework import exceptions
from rest_framework.authentication import TokenAuthentication

LIBRES = ("/api/auth/password/", "/api/whoami/", "/api/licence/")


class BadgeoTokenAuthentication(TokenAuthentication):
    """Un compte à mot de passe provisoire ne peut rien faire d'autre que le changer."""
    def authenticate(self, request):
        res = super().authenticate(request)
        if res and getattr(getattr(res[0], "profile", None), "must_change_password", False) \
                and not request.path.startswith(LIBRES):
            raise exceptions.PermissionDenied({"code": "changement_mot_de_passe",
                                               "detail": "Vous devez d'abord changer votre mot de passe provisoire."})
        return res
