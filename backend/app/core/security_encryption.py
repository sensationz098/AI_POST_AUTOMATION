import base64
import hashlib
import logging
from typing import Optional
from cryptography.fernet import Fernet
from app.core.config import settings

logger = logging.getLogger(__name__)

_fernet_instance: Optional[Fernet] = None

def _get_fernet() -> Fernet:
    global _fernet_instance
    if _fernet_instance is not None:
        return _fernet_instance

    key = settings.TOKEN_ENCRYPTION_KEY
    if not key:
        # Development fallback: derive a deterministic 32-byte key from SECRET_KEY
        hashed = hashlib.sha256(settings.SECRET_KEY.encode("utf-8")).digest()
        key_bytes = base64.urlsafe_b64encode(hashed)
        _fernet_instance = Fernet(key_bytes)
        logger.warning("TOKEN_ENCRYPTION_KEY not set in environment; using derived fallback key for development.")
        return _fernet_instance

    # If raw 32-byte or base64 string provided
    try:
        if len(key) == 44 and key.endswith("="):
            _fernet_instance = Fernet(key.encode("utf-8"))
        else:
            hashed = hashlib.sha256(key.encode("utf-8")).digest()
            key_bytes = base64.urlsafe_b64encode(hashed)
            _fernet_instance = Fernet(key_bytes)
    except Exception as e:
        logger.error(f"Invalid TOKEN_ENCRYPTION_KEY format: {e}. Falling back to derived key.")
        hashed = hashlib.sha256(settings.SECRET_KEY.encode("utf-8")).digest()
        key_bytes = base64.urlsafe_b64encode(hashed)
        _fernet_instance = Fernet(key_bytes)

    return _fernet_instance

def encrypt_token(plain_token: Optional[str]) -> Optional[str]:
    """Encrypt access token before persisting to database."""
    if not plain_token:
        return None
    if plain_token.startswith("enc_gAAAAA"):
        return plain_token  # Already encrypted
    try:
        f = _get_fernet()
        enc_bytes = f.encrypt(plain_token.encode("utf-8"))
        return f"enc_{enc_bytes.decode('utf-8')}"
    except Exception as e:
        logger.error(f"Failed to encrypt access token: {e}")
        return plain_token

def decrypt_token(encrypted_token: Optional[str]) -> Optional[str]:
    """Decrypt access token for internal Graph API service calls."""
    if not encrypted_token:
        return None
    if not encrypted_token.startswith("enc_gAAAAA"):
        return encrypted_token  # Return plaintext token (migration mode)
    try:
        f = _get_fernet()
        raw_enc = encrypted_token[4:].encode("utf-8")
        dec_bytes = f.decrypt(raw_enc)
        return dec_bytes.decode("utf-8")
    except Exception as e:
        logger.error(f"Failed to decrypt access token: {e}")
        return encrypted_token

def mask_token(token: Optional[str]) -> Optional[str]:
    """Mask token for safe logging or debug presentation (e.g. 'EAANNCr...31vn')."""
    if not token:
        return None
    token_str = decrypt_token(token) if token.startswith("enc_gAAAAA") else token
    if len(token_str) <= 12:
        return "****"
    return f"{token_str[:7]}...{token_str[-4:]}"
