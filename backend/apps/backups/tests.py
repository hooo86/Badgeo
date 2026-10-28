import json
import shutil
import tempfile
import zipfile
from datetime import datetime, timedelta
from pathlib import Path

from django.contrib.auth.models import User
from django.core.cache import cache
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.utils import timezone
from rest_framework.authtoken.models import Token

from apps.accounts.models import Profile
from apps.audit.models import AuditLog
from apps.devices.models import Device
from apps.employees.models import Employee
from apps.licensing.models import Licence

from . import services as s

J = "application/json"


class Base(TestCase):
    def setUp(self):
        cache.clear()
        self.tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.tmp, True)
        self.ov = override_settings(BACKUP_DIR=Path(self.tmp) / "b", BACKUP_PASSPHRASE="")
        self.ov.enable()
        self.addCleanup(self.ov.disable)
        self.admin = User.objects.create_superuser("root", password="Str0ng-pass-123")
        self.h = {"HTTP_AUTHORIZATION": f"Token {Token.objects.create(user=self.admin).key}"}


class ServiceTests(Base):
    def test_roundtrip_replaces_data_keeps_licence_and_makes_safety_backup(self):
        dev = Device.objects.create(name="D1", vendor="zkteco", ip_address="10.0.0.2")
        dev.comm_key = 4242
        dev.save()
        Employee.objects.create(matricule="A", first_name="a", last_name="b")
        Licence.objects.create(cle="CLE-ACTUELLE")
        meta = s.creer("manual", "root")
        Employee.objects.create(matricule="B", first_name="c", last_name="d")  # modification après sauvegarde
        Licence.objects.all().update(cle="CLE-NOUVELLE")
        res = s.restaurer(meta["nom"], "root")
        self.assertEqual(sorted(Employee.objects.values_list("matricule", flat=True)), ["A"])
        self.assertEqual(Device.objects.get().comm_key, 4242)               # secret chiffré restauré, lisible avec la même clé
        self.assertEqual(Licence.objects.get().cle, "CLE-NOUVELLE")          # la licence n'est pas touchée
        self.assertTrue(any(m["nom"] == res["sauvegarde_avant"] and m["type"] == "pre_restore" for m in s.lister()))
        # la sauvegarde « avant restauration » permet d'annuler
        s.restaurer(res["sauvegarde_avant"], "root")
        self.assertEqual(sorted(Employee.objects.values_list("matricule", flat=True)), ["A", "B"])

    def test_corruption_and_newer_version_refused_and_database_untouched(self):
        Employee.objects.create(matricule="A", first_name="a", last_name="b")
        meta = s.creer("manual")
        chemin = s.chemin_de(meta["nom"])
        with zipfile.ZipFile(chemin) as z:
            man, data = json.loads(z.read("manifest.json")), z.read("data.json")
        def rewrite(manifest, payload):
            with zipfile.ZipFile(chemin, "w") as z:
                z.writestr("manifest.json", json.dumps(manifest))
                z.writestr("data.json", payload)
        rewrite(man, data.replace(b'"matricule": "A"', b'"matricule": "Z"'))
        with self.assertRaisesMessage(s.SauvegardeError, "corrompue"):
            s.restaurer(meta["nom"])
        rewrite({**man, "migrations": man["migrations"] + ["employees.9999_future"]}, data)
        with self.assertRaisesMessage(s.SauvegardeError, "plus récente"):
            s.restaurer(meta["nom"])
        self.assertEqual(Employee.objects.get().matricule, "A")

    def test_encryption(self):
        Employee.objects.create(matricule="A", first_name="a", last_name="b")
        with override_settings(BACKUP_PASSPHRASE="phrase secrète"):
            meta = s.creer("manual")
            self.assertTrue(meta["chiffree"])
            self.assertNotIn(b"matricule", s.chemin_de(meta["nom"]).read_bytes())
            self.assertEqual(s.verifier(s.chemin_de(meta["nom"]))["lignes"]["employees.employee"], 1)
        with self.assertRaisesMessage(s.SauvegardeError, "phrase de passe"):
            s.verifier(s.chemin_de(meta["nom"]), "")
        with self.assertRaisesMessage(s.SauvegardeError, "incorrecte"):
            s.verifier(s.chemin_de(meta["nom"]), "mauvaise")

    def test_nom_invalide_refuse(self):
        for nom in ("../x.badgeo", "badgeo_1.badgeo", "autre.txt"):
            with self.assertRaises(s.SauvegardeError):
                s.chemin_de(nom)

    def test_retention_et_planification(self):
        s.enregistrer_reglages({"keep": 2, "hour": 0})
        jours = [timezone.now() - timedelta(days=d) for d in (3, 2, 1)]
        for j in jours:
            with self.subTest(j=j):
                m = s.creer("auto")
                p = s.chemin_de(m["nom"]).with_suffix(".json")
                meta = json.loads(p.read_text())
                meta["creee_le"] = j.isoformat()
                p.write_text(json.dumps(meta))
        s.appliquer_retention()
        self.assertEqual(len([m for m in s.lister() if m["type"] == "auto"]), 2)
        made = s.sauvegarde_planifiee()
        self.assertIsNotNone(made)                      # aucune sauvegarde aujourd'hui : en crée une
        self.assertIsNone(s.sauvegarde_planifiee())      # une seule par jour
        s.enregistrer_reglages({"auto": False})
        self.assertIsNone(s.sauvegarde_planifiee(timezone.now() + timedelta(days=1)))

    def test_copie_vers_dossier_externe(self):
        ext = Path(self.tmp) / "usb"
        s.enregistrer_reglages({"copy_dir": str(ext)})
        meta = s.creer("manual")
        self.assertTrue((ext / meta["nom"]).exists())
        fichier = Path(self.tmp) / "un_fichier"
        fichier.write_text("x")
        with self.assertRaises(s.SauvegardeError):  # un dossier ne peut pas être créé sous un fichier, sur tout système
            s.enregistrer_reglages({"copy_dir": str(fichier / "sous-dossier")})


class ApiTests(Base):
    def test_roles_confirmation_import_et_audit(self):
        u = User.objects.create_user("hr", password="Str0ng-pass-123")
        Profile.objects.create(user=u, role="hr_manager")
        hr = {"HTTP_AUTHORIZATION": f"Token {Token.objects.create(user=u).key}"}
        self.assertEqual(self.client.get("/api/backups/", **hr).status_code, 403)
        r = self.client.post("/api/backups/", {}, content_type=J, **self.h)
        self.assertEqual(r.status_code, 201)
        nom = r.json()["nom"]
        self.assertEqual(len(self.client.get("/api/backups/", **self.h).json()["sauvegardes"]), 1)
        self.assertEqual(self.client.post(f"/api/backups/{nom}/restore/", {}, content_type=J, **self.h).status_code, 400)  # sans confirmation
        dl = self.client.get(f"/api/backups/{nom}/", **self.h)
        contenu = b"".join(dl.streaming_content)
        self.assertEqual(dl.status_code, 200)
        up = self.client.post("/api/backups/upload/", {"file": SimpleUploadedFile("x.badgeo", contenu)}, **self.h)
        self.assertEqual((up.status_code, up.json()["type"]), (201, "imported"))
        bad = self.client.post("/api/backups/upload/", {"file": SimpleUploadedFile("x.badgeo", b"pas une sauvegarde")}, **self.h)
        self.assertEqual(bad.status_code, 400)
        ok = self.client.post(f"/api/backups/{nom}/restore/", {"confirmation": "RESTAURER"}, content_type=J, **self.h)
        self.assertEqual(ok.status_code, 200)
        self.assertTrue(AuditLog.objects.filter(action="backup_restore").exists())
        self.assertTrue(AuditLog.objects.filter(action="backup_create").exists())
        self.assertEqual(self.client.delete(f"/api/backups/{nom}/", **self.h).status_code, 401)  # jetons non sauvegardés : reconnexion requise

    def test_audit_trail_survives_restore(self):
        from apps.audit.models import AuditLog
        meta = s.creer("manual")
        nouveau = User.objects.create_user("apres", password="Str0ng-pass-123")
        AuditLog.objects.create(action="evenement_apres_sauvegarde", user=nouveau)
        s.restaurer(meta["nom"])
        self.assertTrue(AuditLog.objects.filter(action="evenement_apres_sauvegarde").exists())
        entree = AuditLog.objects.get(action="evenement_apres_sauvegarde")
        self.assertEqual((entree.user_id, entree.detail["utilisateur_id_supprime"]), (None, nouveau.pk))  # compte absent de la sauvegarde
