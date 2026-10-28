from rest_framework import serializers

from apps.schedules.serializers import CleanedSerializer

from .models import Leave


class LeaveSerializer(CleanedSerializer):
    class Meta:
        model = Leave
        fields = "__all__"
        read_only_fields = ["created_by", "created_at"]

    def create(self, data):
        data["created_by"] = self.context["request"].user
        return super().create(data)
