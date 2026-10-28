import base64
import hashlib
import os

from cryptography.fernet import Fernet
from django.conf import settings


def _fernet() -> Fernet:
    key = os.environ.get("DEVICE_SECRET_KEY")
    if not key:  # dev fallback only; production must set DEVICE_SECRET_KEY (see .env.example)
        key = base64.urlsafe_b64encode(hashlib.sha256(settings.SECRET_KEY.encode()).digest()).decode()
    return Fernet(key.encode())


def encrypt(value: str) -> str:
    return _fernet().encrypt(value.encode()).decode() if value else ""


def decrypt(token: str) -> str:
    return _fernet().decrypt(token.encode()).decode() if token else ""
