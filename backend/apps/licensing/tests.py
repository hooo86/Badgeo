import os
from datetime import timedelta
from unittest import mock

from django.contrib.auth.models import User
from django.core.cache import cache
from django.test import TestCase, override_settings
from django.utils import timezone
from rest_framework.authtoken.models import Token

from apps.accounts.models import Profile
from apps.devices.models import Device
from apps.employees.models import Employee

from . import licence as lic
from .models import Licence

PRIVEE, PUBLIQUE = lic.generer_paire_de_cles()
AUJ = timezone.localdate()
J = "application/json"


@override_settings(BADGEO_LICENCE_CLE_PUBLIQUE=PUBLIQUE)
class CoeurTests(TestCase):
    def setUp(self):
        lic.vider_cache()
        self.addCleanup(lic.vider_cache)
        self.code = lic.code_installation()

    def sign(self, **kw):
        return lic.signer(kw.pop("code", self.code), kw.pop("client", "Société Test"), kw.pop("modules", ["mobile"]),
                          cle_privee=PRIVEE, **kw)

    def test_code_stable_lisible_et_lie_au_poste(self):
        self.assertRegex(self.code, r"^BDG-[A-Z2-9]{4}-[A-Z2-9]{4}-[A-Z2-9]{4}$")
        with mock.patch.dict(os.environ, {"BADGEO_EMPREINTE": "autre-pc"}):
            self.assertNotEqual(self.code, lic.code_installation())

    def test_cle_valide_et_champs(self):
        i = lic.verifier(self.sign(code=self.code.lower(), max_employes=10, max_pointeuses=2, expire_le=AUJ + timedelta(days=30)), self.code)
        self.assertEqual((i.client, i.max_employes, i.max_pointeuses, i.modules, i.jours_restants(), i.essai), ("Société Test", 10, 2, ["mobile"], 30, False))

    def test_cle_refusee(self):
        cle = self.sign()
        with self.assertRaisesMessage(lic.LicenceInvalide, "autre poste"):
            lic.verifier(cle, "BDG-AAAA-BBBB-CCCC")
        with self.assertRaises(lic.LicenceInvalide):
            lic.verifier(cle.replace("BADG1-", "BADG1-X", 1), self.code)
        with self.assertRaises(lic.LicenceInvalide):
            lic.verifier("n'importe quoi", self.code)
        autre, _ = lic.generer_paire_de_cles()
        with self.assertRaisesMessage(lic.LicenceInvalide, "non valable"):
            lic.verifier(lic.signer(self.code, "Pirate", [], cle_privee=autre), self.code)
        with self.assertRaises(lic.LicenceInvalide):
            self.sign(modules=["inconnu"])

    def test_cle_d_essai_tous_postes_exige_une_date(self):
        with self.assertRaises(lic.LicenceInvalide):
            self.sign(code="*")
        i = lic.verifier(self.sign(code="*", expire_le=AUJ + timedelta(days=30)), "BDG-AAAA-BBBB-CCCC")
        self.assertTrue(i.essai)

    def test_recul_de_l_horloge_ne_prolonge_pas(self):
        cle = self.sign(expire_le=AUJ + timedelta(days=2))
        Licence.objects.create(cle=cle, derniere_date=AUJ + timedelta(days=5))
        lic.vider_cache()
        self.assertTrue(lic.verifier(cle, self.code).expiree())
        self.assertTrue(lic.horloge_reculee())


@override_settings(BADGEO_LICENCE_CLE_PUBLIQUE=PUBLIQUE, BADGEO_LICENCE_REQUISE=True)
class EnforcementTests(TestCase):
    def setUp(self):
        cache.clear()
        lic.vider_cache()
        self.addCleanup(lic.vider_cache)
        u = User.objects.create_superuser("root", password="Str0ng-pass-123")
        self.h = {"HTTP_AUTHORIZATION": f"Token {Token.objects.create(user=u).key}"}
        self.code = lic.code_installation()

    def activer(self, **kw):
        cle = lic.signer(self.code, "Client", kw.pop("modules", ["mobile", "reports", "leaves"]), cle_privee=PRIVEE, **kw)
        return self.client.post("/api/licence/", {"cle": cle}, content_type=J, **self.h)

    def test_sans_licence_api_fermee_mais_activation_et_connexion_ouvertes(self):
        r = self.client.get("/api/employees/", **self.h)
        self.assertEqual((r.status_code, r.json()["code"]), (402, "licence_requise"))
        st = self.client.get("/api/licence/").json()
        self.assertEqual((st["requise"], st["active"], st["code_installation"]), (True, False, self.code))
        self.assertEqual(self.client.post("/api/auth/token/", {"username": "root", "password": "x"}).status_code, 400)

    def test_activation_puis_acces_et_mauvaise_cle(self):
        self.assertEqual(self.client.post("/api/licence/", {"cle": "BADG1-xxx.yyy"}, content_type=J).status_code, 400)
        r = self.activer(max_employes=2, expire_le=AUJ + timedelta(days=10))
        self.assertEqual(r.status_code, 200)
        self.assertTrue(r.json()["active"])
        self.assertEqual(self.client.get("/api/employees/", **self.h).status_code, 200)

    def test_remplacer_la_licence_exige_un_administrateur(self):
        self.activer()
        u = User.objects.create_user("hr", password="Str0ng-pass-123")
        Profile.objects.create(user=u, role="hr_manager")
        h = {"HTTP_AUTHORIZATION": f"Token {Token.objects.create(user=u).key}"}
        cle = lic.signer(self.code, "X", [], cle_privee=PRIVEE)
        self.assertEqual(self.client.post("/api/licence/", {"cle": cle}, content_type=J, **h).status_code, 403)

    def test_expiree_lecture_seule(self):
        self.activer(expire_le=AUJ - timedelta(days=1))
        self.assertEqual(self.client.get("/api/employees/", **self.h).status_code, 200)
        r = self.client.post("/api/employees/", {"matricule": "A", "first_name": "a", "last_name": "b"}, content_type=J, **self.h)
        self.assertEqual((r.status_code, r.json()["code"]), (402, "licence_expiree"))
        self.assertNotEqual(self.client.post("/api/backups/", {}, content_type=J, **self.h).status_code, 402)  # sauvegarde toujours possible

    def test_modules(self):
        self.activer(modules=["mobile"])
        self.assertEqual(self.client.get("/api/leaves/", **self.h).status_code, 403)
        self.assertEqual(self.client.get("/api/reports/daily/", **self.h).json()["code"], "module_non_licencie")
        self.assertEqual(self.client.get("/api/me/", **self.h).status_code, 403)  # pas de module refusé : compte sans employé
        self.assertNotEqual(self.client.get("/api/me/", **self.h).json().get("code"), "module_non_licencie")

    def test_plafonds(self):
        self.activer(max_employes=1, max_pointeuses=1)
        body = {"matricule": "A", "first_name": "a", "last_name": "b"}
        self.assertEqual(self.client.post("/api/employees/", body, content_type=J, **self.h).status_code, 201)
        r = self.client.post("/api/employees/", {**body, "matricule": "B"}, content_type=J, **self.h)
        self.assertEqual(r.status_code, 400)
        self.assertIn("Plafond", r.json()["detail"])
        Employee.objects.filter(matricule="A").update(status="left")  # une place se libère
        self.assertEqual(self.client.post("/api/employees/", {**body, "matricule": "B"}, content_type=J, **self.h).status_code, 201)
        dev = {"name": "D1", "vendor": "zkteco", "ip_address": "10.0.0.2"}
        self.assertEqual(self.client.post("/api/devices/", dev, content_type=J, **self.h).status_code, 201)
        self.assertEqual(self.client.post("/api/devices/", {**dev, "name": "D2", "ip_address": "10.0.0.3"}, content_type=J, **self.h).status_code, 400)
        self.assertEqual(Device.objects.count(), 1)
