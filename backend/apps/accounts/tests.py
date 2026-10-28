from django.contrib.auth.models import User
from django.core.cache import cache
from django.test import TestCase
from rest_framework.authtoken.models import Token

from apps.audit.models import AuditLog
from apps.devices.models import Device
from apps.employees.models import Employee
from apps.orgs.models import OrgUnit

from .models import Profile


def make_user(name, role, scopes=()):
    u = User.objects.create_user(name, password="Str0ng-pass-123")
    p = Profile.objects.create(user=u, role=role)
    p.scopes.set(scopes)
    return {"HTTP_AUTHORIZATION": f"Token {Token.objects.create(user=u).key}"}


class RoleTests(TestCase):
    def setUp(self):
        cache.clear()
        self.dir_a = OrgUnit.objects.create(kind="direction", name="A")
        self.svc_a = OrgUnit.objects.create(kind="service", name="A1", parent=self.dir_a)
        self.dir_b = OrgUnit.objects.create(kind="direction", name="B")
        Employee.objects.create(matricule="1", first_name="x", last_name="a", org_unit=self.svc_a)
        Employee.objects.create(matricule="2", first_name="y", last_name="b", org_unit=self.dir_b)

    def test_anonymous_rejected(self):
        self.assertEqual(self.client.get("/api/devices/").status_code, 401)

    def test_device_admin_creates_device_with_encrypted_key_and_audit(self):
        h = make_user("da", "device_admin")
        r = self.client.post("/api/devices/", {"name": "X", "vendor": "zkteco", "ip_address": "10.0.0.9", "comm_key": 1234},
                             content_type="application/json", **h)
        self.assertEqual(r.status_code, 201)
        self.assertNotIn("comm_key", r.json())
        d = Device.objects.get()
        self.assertEqual(d.comm_key, 1234)
        self.assertNotIn("1234", d.comm_key_enc)
        log = AuditLog.objects.get(action="create", object_type="devices.Device")
        self.assertNotIn("comm_key", str(log.after))

    def test_hr_cannot_write_devices_viewer_cannot_read_them(self):
        body = {"name": "Y", "vendor": "zkteco", "ip_address": "10.0.0.8"}
        self.assertEqual(self.client.post("/api/devices/", body, content_type="application/json",
                                          **make_user("hr", "hr_staff")).status_code, 403)
        self.assertEqual(self.client.get("/api/devices/", **make_user("v", "viewer")).status_code, 403)

    def test_scope_restricts_employees_including_descendants(self):
        h = make_user("dh", "dept_head", [self.dir_a])
        self.assertEqual([e["matricule"] for e in self.client.get("/api/employees/", **h).json()["results"]], ["1"])
        self.assertEqual(self.client.get("/api/employees/", **make_user("noscope", "viewer")).json()["count"], 0)
        self.assertEqual(self.client.get("/api/employees/", **make_user("hm", "hr_manager")).json()["count"], 2)
        self.assertEqual(self.client.post("/api/employees/", {}, content_type="application/json", **h).status_code, 403)

    def test_only_sysadmin_manages_users(self):
        self.assertEqual(self.client.get("/api/users/", **make_user("hm", "hr_manager")).status_code, 403)
        root = User.objects.create_superuser("root", password="Str0ng-pass-123")
        h = {"HTTP_AUTHORIZATION": f"Token {Token.objects.create(user=root).key}"}
        weak = self.client.post("/api/users/", {"username": "n", "role": "viewer", "password": "123"},
                                content_type="application/json", **h)
        self.assertEqual(weak.status_code, 400)
        ok = self.client.post("/api/users/", {"username": "n", "role": "viewer", "password": "Str0ng-pass-123"},
                              content_type="application/json", **h)
        self.assertEqual(ok.status_code, 201)

    def test_login_throttled_and_audited(self):
        User.objects.create_user("bob", password="Str0ng-pass-123")
        codes = [self.client.post("/api/auth/token/", {"username": "bob", "password": "bad"}).status_code for _ in range(7)]
        self.assertEqual(codes[:5], [400] * 5)
        self.assertEqual(codes[-1], 429)
        self.assertEqual(AuditLog.objects.filter(action="login_failed").count(), 5)

    def test_audit_log_immutable(self):
        log = AuditLog.objects.create(action="x")
        log.action = "y"
        with self.assertRaises(PermissionError):
            log.save()


class PasswordTests(TestCase):
    def setUp(self):
        cache.clear()

    def test_provisional_password_blocks_everything_until_changed(self):
        u = User.objects.create_user("prov", password="Provisoire-123!")
        Profile.objects.create(user=u, role="hr_manager", must_change_password=True)
        h = {"HTTP_AUTHORIZATION": f"Token {Token.objects.create(user=u).key}"}
        r = self.client.get("/api/employees/", **h)
        self.assertEqual((r.status_code, r.json()["code"]), (403, "changement_mot_de_passe"))
        self.assertTrue(self.client.get("/api/whoami/", **h).json()["must_change_password"])
        json = "application/json"
        self.assertEqual(self.client.post("/api/auth/password/", {"ancien": "faux", "nouveau": "Nouveau-Passe-456!"}, content_type=json, **h).status_code, 400)
        self.assertEqual(self.client.post("/api/auth/password/", {"ancien": "Provisoire-123!", "nouveau": "123"}, content_type=json, **h).status_code, 400)
        ok = self.client.post("/api/auth/password/", {"ancien": "Provisoire-123!", "nouveau": "Nouveau-Passe-456!"}, content_type=json, **h)
        self.assertEqual(ok.status_code, 200)
        h2 = {"HTTP_AUTHORIZATION": f"Token {ok.json()['token']}"}
        self.assertEqual(self.client.get("/api/employees/", **h2).status_code, 200)
        self.assertEqual(self.client.get("/api/employees/", **h).status_code, 401)  # ancien jeton révoqué

    def test_admin_set_password_is_provisional(self):
        root = User.objects.create_superuser("root", password="Str0ng-pass-123")
        h = {"HTTP_AUTHORIZATION": f"Token {Token.objects.create(user=root).key}"}
        r = self.client.post("/api/users/", {"username": "n", "role": "viewer", "password": "Str0ng-pass-123"}, content_type="application/json", **h)
        self.assertTrue(User.objects.get(username="n").profile.must_change_password)
        self.assertTrue(r.json()["must_change_password"])


class InitialAdminTests(TestCase):
    def test_default_admin_is_provisional_and_created_once(self):
        from django.core.management import call_command
        call_command("initialiser_local", stdout=__import__("io").StringIO())
        u = User.objects.get(username="admin")
        self.assertTrue(u.check_password("Badgeo@2026"))
        self.assertTrue(u.profile.must_change_password and u.is_superuser)
        u.set_password("Autre-Passe-2026!")
        u.save()
        call_command("initialiser_local", stdout=__import__("io").StringIO())  # ne recrée ni ne réinitialise rien
        self.assertEqual(User.objects.count(), 1)
        self.assertTrue(User.objects.get(username="admin").check_password("Autre-Passe-2026!"))


class ResetAdminTests(TestCase):
    def test_reset_restores_default_credentials_and_revokes_tokens(self):
        import io
        from django.core.management import call_command
        u = User.objects.create_user("admin", password="Mot-de-passe-oublie-1!")
        u.is_active = False
        u.save()
        Token.objects.create(user=u)
        call_command("reinitialiser_admin", stdout=io.StringIO())
        u.refresh_from_db()
        self.assertTrue(u.check_password("Badgeo@2026") and u.is_active and u.is_superuser)
        self.assertTrue(u.profile.must_change_password)
        self.assertFalse(Token.objects.filter(user=u).exists())
        self.assertTrue(AuditLog.objects.filter(action="admin_reinitialise").exists())
