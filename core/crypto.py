import os
import base64
import json
import logging
from pathlib import Path

from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

from .log_utils import log_call

logger = logging.getLogger(__name__)

KEY_FILE = "vault.key"
SALT = b"myvpn_salt_2026_v1"


def _get_key_path() -> Path:
    import platform
    if platform.system() == "Windows":
        base = Path(os.environ.get("APPDATA", Path.home() / "AppData" / "Roaming"))
    else:
        base = Path.home() / ".config"
    key_path = base / "my_vpn" / KEY_FILE
    logger.debug("Key path resolved: %s", key_path)
    return key_path


@log_call()
def get_or_create_vault() -> Fernet:
    key_path = _get_key_path()
    key_path.parent.mkdir(parents=True, exist_ok=True)

    if key_path.exists():
        with open(key_path, "rb") as f:
            key = f.read()
        logger.info("Vault key loaded from %s (size=%d)", key_path, len(key))
    else:
        key = Fernet.generate_key()
        with open(key_path, "wb") as f:
            f.write(key)
        logger.info("Vault key GENERATED at %s (size=%d)", key_path, len(key))

    return Fernet(key)


@log_call()
def encrypt_dict(data: dict, vault: Fernet) -> str:
    plain = json.dumps(data, ensure_ascii=False, separators=(",", ":"))
    logger.debug("Encrypting dict: %d bytes plaintext", len(plain))
    encrypted = vault.encrypt(plain.encode("utf-8"))
    result = base64.urlsafe_b64encode(encrypted).decode("ascii")
    logger.debug("Encrypted: %d bytes → %d chars", len(encrypted), len(result))
    return result


@log_call()
def decrypt_dict(encrypted_str: str, vault: Fernet) -> dict:
    logger.debug("Decrypting: %d chars", len(encrypted_str))
    encrypted = base64.urlsafe_b64decode(encrypted_str.encode("ascii"))
    plain = vault.decrypt(encrypted)
    result = json.loads(plain.decode("utf-8"))
    logger.debug("Decrypted: %d bytes → %d fields", len(plain), len(result))
    return result


@log_call()
def encrypt_field(value: str, vault: Fernet) -> str:
    if not value:
        return ""
    encrypted = vault.encrypt(value.encode("utf-8"))
    result = base64.urlsafe_b64encode(encrypted).decode("ascii")
    logger.debug("Field encrypted: %d chars → %d chars", len(value), len(result))
    return result


@log_call()
def decrypt_field(encrypted_str: str, vault: Fernet) -> str:
    if not encrypted_str:
        return ""
    encrypted = base64.urlsafe_b64decode(encrypted_str.encode("ascii"))
    result = vault.decrypt(encrypted).decode("utf-8")
    return result
