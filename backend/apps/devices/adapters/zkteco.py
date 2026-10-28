import socket

from .base import BaseAdapter, DeviceError, RawPunch


class ZKAdapter(BaseAdapter):
    def _connect(self):
        try:
            from zk import ZK
        except ImportError as e:  # pragma: no cover
            raise DeviceError("pyzk is not installed", "protocol") from e
        d = self.device
        zk = ZK(d.ip_address, port=d.port, timeout=10, password=d.comm_key,
                force_udp=d.protocol == "zk_udp", ommit_ping=True)
        try:
            return zk.connect()
        except (socket.timeout, TimeoutError, OSError) as e:
            raise DeviceError(f"Network error {d.ip_address}:{d.port}: {e}", "network") from e
        except Exception as e:
            msg = str(e)
            stage = "auth" if "auth" in msg.lower() else "protocol"
            raise DeviceError(msg, stage) from e

    def test(self):
        conn = self._connect()
        try:
            return {"serial_number": conn.get_serialnumber(), "firmware": conn.get_firmware_version(),
                    "time": conn.get_time()}
        finally:
            conn.disconnect()

    def fetch_punches(self):
        conn = self._connect()
        try:
            return [RawPunch(str(a.user_id), a.timestamp, a.punch or 0, a.status or 0)
                    for a in conn.get_attendance()]
        except DeviceError:
            raise
        except Exception as e:
            raise DeviceError(f"Read failed: {e}", "protocol") from e
        finally:
            conn.disconnect()
