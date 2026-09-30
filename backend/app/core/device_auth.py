import hashlib
import hmac
import json
from collections.abc import Mapping

from app.config import settings


class DeviceAuthService:
    """Verifies device event signatures using a shared development HMAC secret."""

    def __init__(self, secret: str | None = None) -> None:
        self._secret = (secret or settings.device_hmac_secret).encode("utf-8")

    def create_signature(self, payload: Mapping[str, object]) -> str:
        canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"))
        message = canonical.encode("utf-8")
        return hmac.new(self._secret, message, hashlib.sha256).hexdigest()

    def verify_signature(self, payload: Mapping[str, object], signature: str) -> bool:
        expected = self.create_signature(payload)
        return hmac.compare_digest(expected, signature.lower())


device_auth_service = DeviceAuthService()
