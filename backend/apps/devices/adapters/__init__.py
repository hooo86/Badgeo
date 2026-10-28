from .base import BaseAdapter, DeviceError, RawPunch  # noqa: F401
from .unis import UnisAdapter
from .zkteco import ZKAdapter

ADAPTERS = {"zkteco": ZKAdapter, "unis": UnisAdapter}


def get_adapter(device) -> "BaseAdapter":
    return ADAPTERS[device.vendor](device)
