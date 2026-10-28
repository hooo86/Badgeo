from rest_framework import serializers

from apps.attendance.models import AttendanceDay
from apps.attendance.services import recompute_day

from .models import Correction
from .services import OVERRIDE_STATUSES, snapshot


class CorrectionSerializer(serializers.ModelSerializer):
    reason = serializers.CharField(min_length=5)

    class Meta:
        model = Correction
        fields = "__all__"
        read_only_fields = ["initial", "created_by", "created_at", "state", "reviewed_by", "reviewed_at",
                            "review_note", "result_punch", "after"]

    def validate(self, data):
        if data["kind"] == Correction.Kind.ADD_PUNCH and not data.get("new_timestamp"):
            raise serializers.ValidationError({"new_timestamp": "Requis pour ajouter un pointage."})
        if data["kind"] == Correction.Kind.SET_STATUS and data.get("new_status") not in OVERRIDE_STATUSES:
            raise serializers.ValidationError({"new_status": f"Choisir parmi {sorted(OVERRIDE_STATUSES)}."})
        return data

    def create(self, data):
        day = AttendanceDay.objects.filter(employee=data["employee"], work_date=data["work_date"]).first() \
            or recompute_day(data["employee"], data["work_date"])
        data["initial"] = snapshot(day)
        data["created_by"] = self.context["request"].user
        return super().create(data)
