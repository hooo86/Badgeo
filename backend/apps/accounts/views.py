from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers, viewsets
from rest_framework.authtoken.models import Token
from rest_framework.authtoken.views import ObtainAuthToken
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle

from apps.audit.utils import audit, AuditMixin

from .models import Profile, Role

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

    class Meta:
        model = User
        fields = ["id", "username", "first_name", "last_name", "email", "is_active", "role", "scopes", "password"]

    def validate_password(self, value):
        validate_password(value)
        return value

    def create(self, data):
        prof = data.pop("profile", {})
        pwd = data.pop("password", None)
        user = User(**data)
        user.set_password(pwd) if pwd else user.set_unusable_password()
        user.save()
        p = Profile.objects.create(user=user, role=prof.get("role", Role.VIEWER))
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
