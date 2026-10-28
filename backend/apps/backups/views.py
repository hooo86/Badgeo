from django.contrib.auth.models import User
from django.http import FileResponse
from rest_framework.parsers import JSONParser, MultiPartParser
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.audit.models import AuditLog
from apps.audit.utils import audit

from . import services as s


def _erreur(e):
    return Response({"detail": str(e)}, status=400)


class Racine(APIView):
    """GET : réglages et liste. POST : sauvegarde manuelle. Réservé à l'administrateur système."""
    role_rules = {"read": {"sysadmin"}, "write": {"sysadmin"}}

    def get(self, request):
        return Response({"reglages": s.reglages(), "dossier": str(s.dossier()), "chiffrement": bool(s.settings.BACKUP_PASSPHRASE),
                         "sauvegardes": s.lister()})

    def post(self, request):
        try:
            meta = s.creer("manual", request.user.get_username())
        except s.SauvegardeError as e:
            return _erreur(e)
        audit(request, "backup_create", detail={"nom": meta["nom"], "taille": meta["taille"]})
        return Response(meta, status=201)


class Reglages(APIView):
    role_rules = {"read": {"sysadmin"}, "write": {"sysadmin"}}

    def put(self, request):
        try:
            cfg = s.enregistrer_reglages(request.data)
        except (s.SauvegardeError, ValueError, TypeError) as e:
            return _erreur(e)
        audit(request, "backup_settings", after=cfg)
        return Response(cfg)


class Detail(APIView):
    role_rules = {"read": {"sysadmin"}, "write": {"sysadmin"}}

    def get(self, request, nom):  # téléchargement
        try:
            p = s.chemin_de(nom)
        except s.SauvegardeError as e:
            return _erreur(e)
        audit(request, "backup_download", detail={"nom": nom})
        return FileResponse(open(p, "rb"), as_attachment=True, filename=nom)

    def delete(self, request, nom):
        try:
            s.supprimer(nom)
        except s.SauvegardeError as e:
            return _erreur(e)
        audit(request, "backup_delete", detail={"nom": nom})
        return Response(status=204)


class Restaurer(APIView):
    role_rules = {"read": {"sysadmin"}, "write": {"sysadmin"}}

    def post(self, request, nom):
        if request.data.get("confirmation") != s.CONFIRMATION:
            return Response({"detail": f"Tapez « {s.CONFIRMATION} » pour confirmer : toutes les données actuelles seront remplacées."}, status=400)
        try:
            res = s.restaurer(nom, request.user.get_username(), request.data.get("phrase_de_passe") or None)
        except s.SauvegardeError as e:
            return _erreur(e)
        # la restauration remplace les comptes : l'auteur n'existe peut-être plus dans les nouvelles données
        existe = User.objects.filter(pk=request.user.pk).exists()
        AuditLog.objects.create(user=request.user if existe else None, action="backup_restore", detail=res,
                                ip=request.META.get("REMOTE_ADDR") or None)
        return Response(res)


class Importer(APIView):
    role_rules = {"read": {"sysadmin"}, "write": {"sysadmin"}}
    parser_classes = [MultiPartParser]

    def post(self, request):
        f = request.FILES.get("file")
        if not f:
            return Response({"detail": "Fichier manquant (champ 'file')."}, status=400)
        if f.size > 2 * 1024 ** 3:
            return Response({"detail": "Fichier trop volumineux."}, status=400)
        try:
            meta = s.importer(f.read(), request.data.get("phrase_de_passe") or None)
        except s.SauvegardeError as e:
            return _erreur(e)
        audit(request, "backup_import", detail={"nom": meta["nom"]})
        return Response(meta, status=201)
