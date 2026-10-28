from rest_framework import serializers

from .models import OrgUnit


class OrgUnitSerializer(serializers.ModelSerializer):
    class Meta:
        model = OrgUnit
        fields = "__all__"
