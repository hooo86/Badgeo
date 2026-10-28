from rest_framework import serializers

from .models import AttendanceDay, PunchEvent


class PunchEventSerializer(serializers.ModelSerializer):
    device_name = serializers.CharField(source="device.name", read_only=True, default=None)
    employee_name = serializers.SerializerMethodField()

    class Meta:
        model = PunchEvent
        fields = "__all__"

    def get_employee_name(self, o):
        return f"{o.employee.last_name} {o.employee.first_name}" if o.employee else None


class AttendanceDaySerializer(serializers.ModelSerializer):
    employee_name = serializers.SerializerMethodField()
    matricule = serializers.CharField(source="employee.matricule", read_only=True)
    shift_name = serializers.CharField(source="shift.name", read_only=True, default=None)

    class Meta:
        model = AttendanceDay
        fields = "__all__"

    def get_employee_name(self, o):
        return f"{o.employee.last_name} {o.employee.first_name}"
