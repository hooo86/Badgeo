from rest_framework import serializers

from .models import Device, SyncLog


class DeviceSerializer(serializers.ModelSerializer):
    comm_key = serializers.IntegerField(write_only=True, required=False, min_value=0)

    def create(self, data):
        key = data.pop("comm_key", 0)
        d = Device(**data)
        d.comm_key = key
        d.save()
        return d

    def update(self, d, data):
        if "comm_key" in data:
            d.comm_key = data.pop("comm_key")
        return super().update(d, data)

    class Meta:
        model = Device
        exclude = ["comm_key_enc"]
        read_only_fields = ["status", "last_error", "last_seen_at", "last_sync_at", "last_sync_ok",
                            "events_total", "consecutive_failures"]


class SyncLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = SyncLog
        fields = "__all__"
