from rest_framework import serializers

from .models import DeviceUserMap, Employee


class EmployeeSerializer(serializers.ModelSerializer):
    org_unit_name = serializers.CharField(source="org_unit.name", read_only=True, default=None)

    class Meta:
        model = Employee
        fields = "__all__"


class DeviceUserMapSerializer(serializers.ModelSerializer):
    class Meta:
        model = DeviceUserMap
        fields = "__all__"
