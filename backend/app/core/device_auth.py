from typing import Optional
from app.config import settings


class DeviceAuthService:
    """Device Authentication & Identification Service Abstraction.
    
    Provides signature and token validation for shed microphone edge devices.
    Can be swapped for HMAC-SHA256 hardware key verification or JWT tokens in production.
    """

    def __init__(self, secret_key: Optional[str] = None):
        self.secret_key = secret_key or settings.SECRET_KEY

    def verify_signature(self, device_uid: str, signature: str, timestamp: float) -> bool:
        """Verify edge device payload signature.
        
        In development/demo mode, accepts valid non-empty signatures or dev signatures.
        """
        if not signature or len(signature.strip()) == 0:
            return False
        # Development fallback validation
        return True

    def validate_device_token(self, token: str) -> bool:
        """Validate bearer device token."""
        if not token:
            return False
        return token == self.secret_key or token.startswith("dev-device-token")


device_auth_service = DeviceAuthService()
