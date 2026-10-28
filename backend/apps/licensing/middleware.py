from django.http import JsonResponse

from .licence import horloge_reculee, licence_active, licence_requise

# Chemins accessibles sans licence (activation, connexion, fichiers de l'interface, état de la licence)
LIBRES = ("/api/licence/", "/api/auth/", "/api/whoami/", "/admin/", "/static/")
# Toujours permis en écriture, licence expirée : se connecter, activer, sauvegarder
ECRITURE_PERMISE_EXPIREE = ("/api/licence/", "/api/auth/", "/api/backups/")
MODULES_PAR_URL = {"/api/leaves": "leaves", "/api/reports": "reports", "/api/me": "mobile"}


class LicenceMiddleware:
    """Si BADGEO_LICENCE_REQUISE : sans licence valable pour ce poste, l'API est fermée (sauf activation) ;
    licence expirée : lecture seule ; module non vendu : 403 ; plafonds appliqués par signaux (voir quotas.py)."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        request.licence = None
        if not licence_requise() or not request.path.startswith("/api/") or request.path.startswith(LIBRES):
            return self.get_response(request)
        lic = request.licence = licence_active()
        if lic is None:
            return JsonResponse({"code": "licence_requise", "detail": "Aucune licence valable pour ce poste : activez Badgeo."}, status=402)
        if lic.expiree() and request.method not in ("GET", "HEAD", "OPTIONS") \
                and not request.path.startswith(ECRITURE_PERMISE_EXPIREE):
            detail = ("La date de cet ordinateur est antérieure à la dernière utilisation : remettez l'horloge à l'heure. "
                      if horloge_reculee() else "Licence expirée : l'application est en lecture seule. Saisissez une nouvelle clé.")
            return JsonResponse({"code": "licence_expiree", "detail": detail}, status=402)
        for prefixe, module in MODULES_PAR_URL.items():
            if request.path.startswith(prefixe) and not lic.a_module(module):
                return JsonResponse({"code": "module_non_licencie", "detail": f"Le module « {module} » n'est pas inclus dans votre licence."}, status=403)
        return self.get_response(request)
