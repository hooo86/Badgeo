from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import serializers, viewsets
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.authtoken.models import Token
from rest_framework.authtoken.views import ObtainAuthToken
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle

from apps.audit.utils import audit, AuditMixin

from .models import Profile, Role, get_role

User = get_user_model()


class LoginView(ObtainAuthToken):
    throttle_scope = "login"
    throttle_classes = [ScopedRateThrottle]  # ObtainAuthToken disables throttling by default
    authentication_classes = []
    permission_classes = []

    def post(self, request, *args, **kwargs):
        ser = self.get_serializer(data=request.data)
        if not ser.is_valid():
            audit(request, "login_failed", detail={"username": str(request.data.get("username", ""))[:150]})
            ser.is_valid(raise_exception=True)
        user = ser.validated_data["user"]
        token, _ = Token.objects.get_or_create(user=user)
        audit(request, "login", user=user)
        return Response({"token": token.key})


class UserSerializer(serializers.ModelSerializer):
    role = serializers.ChoiceField(choices=Role.choices, source="profile.role")
    scopes = serializers.PrimaryKeyRelatedField(many=True, read_only=False, required=False,
                                                source="profile.scopes", queryset=Profile.scopes.rel.model.objects.all())
    password = serializers.CharField(write_only=True, required=False)
    must_change_password = serializers.BooleanField(source="profile.must_change_password", required=False)

    class Meta:
        model = User
        fields = ["id", "username", "first_name", "last_name", "email", "is_active", "role", "scopes", "password",
                  "must_change_password"]

    def validate_password(self, value):
        validate_password(value)
        return value

    def create(self, data):
        prof = data.pop("profile", {})
        pwd = data.pop("password", None)
        user = User(**data)
        user.set_password(pwd) if pwd else user.set_unusable_password()
        user.save()
        p = Profile.objects.create(user=user, role=prof.get("role", Role.VIEWER),
                                   must_change_password=prof.get("must_change_password", bool(pwd)))
        p.scopes.set(prof.get("scopes", []))
        return user

    def update(self, user, data):
        prof = data.pop("profile", {})
        pwd = data.pop("password", None)
        for k, v in data.items():
            setattr(user, k, v)
        if pwd:
            user.set_password(pwd)
            Token.objects.filter(user=user).delete()  # force re-login after password change
        user.save()
        p, _ = Profile.objects.get_or_create(user=user)
        if "role" in prof:
            p.role = prof["role"]
        if "must_change_password" in prof or pwd:
            p.must_change_password = prof.get("must_change_password", True)  # mot de passe posé par un admin = provisoire
        p.save()
        if "scopes" in prof:
            p.scopes.set(prof["scopes"])
        return user


class UserViewSet(AuditMixin, viewsets.ModelViewSet):
    queryset = User.objects.select_related("profile").order_by("username")
    serializer_class = UserSerializer
    role_rules = {"read": {"sysadmin"}, "write": {"sysadmin"}}
    search_fields = ["username", "first_name", "last_name", "email"]
    audit_exclude = ("password",)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def whoami(request):
    u = request.user
    return Response({"username": u.get_username(), "name": u.get_full_name() or u.get_username(),
                     "role": get_role(u), "has_employee": hasattr(u, "employee"),
                     "must_change_password": bool(getattr(getattr(u, "profile", None), "must_change_password", False))})


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def change_password(request):
    u = request.user
    if not u.check_password(request.data.get("ancien", "")):
        audit(request, "password_change_failed")
        return Response({"detail": "Mot de passe actuel incorrect."}, status=400)
    nouveau = request.data.get("nouveau", "")
    try:
        validate_password(nouveau, u)
    except DjangoValidationError as e:
        return Response({"detail": " ".join(e.messages)}, status=400)
    if nouveau == request.data.get("ancien"):
        return Response({"detail": "Le nouveau mot de passe doit être différent."}, status=400)
    u.set_password(nouveau)
    u.save()
    Profile.objects.filter(user=u).update(must_change_password=False)
    Token.objects.filter(user=u).delete()
    audit(request, "password_changed")
    return Response({"token": Token.objects.create(user=u).key})
