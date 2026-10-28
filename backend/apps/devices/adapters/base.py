from dataclasses import dataclass
from datetime import datetime
from typing import Iterable


class DeviceError(Exception):
    """Communication failure; `stage` says where (network, auth, protocol)."""
    def __init__(self, message, stage="protocol"):
        super().__init__(message)
        self.stage = stage


@dataclass(frozen=True)
class RawPunch:
    device_user_id: str
    timestamp: datetime  # naive, in the device's local clock
    punch_type: int = 0
    verify_mode: int = 0


class BaseAdapter:
    def __init__(self, device):
        self.device = device

    def test(self) -> dict:
        """Connect and return {'serial_number', 'firmware', 'time'}; raise DeviceError."""
        raise NotImplementedError

    def fetch_punches(self) -> Iterable[RawPunch]:
        """Return all punches stored on the device. Must NOT clear the device memory."""
        raise NotImplementedError
