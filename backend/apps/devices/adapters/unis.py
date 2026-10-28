from .base import BaseAdapter, DeviceError


class UnisAdapter(BaseAdapter):
    """Placeholder: UNIS terminals do not share one documented protocol across models.
    Implement once the exact model and its SDK/HTTP API are confirmed."""

    def test(self):
        raise DeviceError("UNIS adapter not implemented for this model yet", "protocol")

    fetch_punches = test
