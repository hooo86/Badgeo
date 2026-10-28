from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from apps.accounts.models import get_role
from apps.audit.utils import audit
from apps.devices.models import Device
from apps.employees.models import Employee

from . import licence as lic
from .models import Licence


def _etat(avec_usage=False):
    infos = lic.licence_active() if lic.licence_requise() else None
    out = {"requise": lic.licence_requise(), "code_installation": lic.code_installation(), "active": infos is not None,
           "modules_disponibles": lic.MODULES}
    if infos:
        out["licence"] = {"numero": infos.numero, "client": infos.client, "modules": infos.modules, "essai": infos.essai,
                          "max_employes": infos.max_employes, "max_pointeuses": infos.max_pointeuses,
                          "expire_le": infos.expire_le, "jours_restants": infos.jours_restants(),
                          "expiree": infos.expiree(), "horloge_reculee": lic.horloge_reculee()}
        if avec_usage:
            out["usage"] = {"employes": Employee.objects.filter(status="active").count(), "pointeuses": Device.objects.count()}
    return out


@api_view(["GET", "POST"])
@permission_classes([AllowAny])
def licence(request):
    """GET : état (public : l'écran d'activation doit s'afficher avant la connexion). POST : activer une clé."""
    if request.method == "GET":
        autorise = getattr(request.user, "is_authenticated", False)
        return Response(_etat(avec_usage=autorise))
    if lic.licence_requise() and lic.licence_active() is not None and get_role(request.user) != "sysadmin":
        return Response({"detail": "Seul l'administrateur système peut remplacer la licence."}, status=403)
    code = lic.code_installation()
    try:
        infos = lic.verifier(request.data.get("cle", ""), code)
    except lic.LicenceInvalide as e:
        audit(request, "licence_refusee", detail={"motif": str(e)})
        return Response({"detail": str(e)}, status=400)
    import re
    Licence.objects.all().delete()
    Licence.objects.create(cle=re.sub(r"\s+", "", request.data["cle"]))
    lic.vider_cache()
    audit(request, "licence_activee", detail={"numero": infos.numero, "client": infos.client})
    return Response(_etat())
