from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import serializers

from .models import Holiday, Rotation, Shift, ShiftAssignment


class CleanedSerializer(serializers.ModelSerializer):
    """Runs the model's clean() so API and admin enforce the same rules."""
    def validate(self, data):
        inst = self.Meta.model(**{k: v for k, v in data.items() if k in {f.name for f in self.Meta.model._meta.fields}})
        try:
            inst.clean()
        except DjangoValidationError as e:
            raise serializers.ValidationError(e.messages)
        return data


class ShiftSerializer(CleanedSerializer):
    crosses_midnight = serializers.BooleanField(read_only=True)
    expected_minutes = serializers.IntegerField(read_only=True)

    class Meta:
        model = Shift
        fields = "__all__"


class RotationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Rotation
        fields = "__all__"

    def validate_cycle(self, cycle):
        ids = {c for c in cycle if c is not None}
        if ids - set(Shift.objects.filter(pk__in=ids).values_list("pk", flat=True)):
            raise serializers.ValidationError("Horaire inconnu dans le cycle.")
        return cycle


class AssignmentSerializer(CleanedSerializer):
    class Meta:
        model = ShiftAssignment
        fields = "__all__"


class HolidaySerializer(serializers.ModelSerializer):
    class Meta:
        model = Holiday
        fields = "__all__"
