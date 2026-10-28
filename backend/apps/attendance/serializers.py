from rest_framework import serializers

from .models import PunchEvent


class PunchEventSerializer(serializers.ModelSerializer):
    class Meta:
        model = PunchEvent
        fields = "__all__"
