"""
Field Encryption Utility
========================
Provides encryption/decryption for sensitive database fields.
Uses Fernet symmetric encryption with key derived from SECRET_KEY.
"""

import base64
import hashlib
from typing import Optional
from cryptography.fernet import Fernet, InvalidToken
from functools import lru_cache

from app.core.config import get_settings


@lru_cache()
def get_encryption_key() -> bytes:
    """
    Derive a Fernet-compatible key from the application SECRET_KEY.
    Fernet requires a 32-byte base64-encoded key.
    """
    settings = get_settings()
    # Use SHA256 to get consistent 32 bytes from any secret key length
    key_hash = hashlib.sha256(settings.secret_key.encode()).digest()
    return base64.urlsafe_b64encode(key_hash)


@lru_cache()
def get_fernet() -> Fernet:
    """Get cached Fernet instance."""
    return Fernet(get_encryption_key())


def encrypt_value(plaintext: str) -> str:
    """
    Encrypt a string value.
    
    Args:
        plaintext: The string to encrypt
        
    Returns:
        Base64-encoded encrypted string prefixed with 'enc:'
    """
    if not plaintext:
        return plaintext
    
    # Don't re-encrypt already encrypted values
    if plaintext.startswith('enc:'):
        return plaintext
    
    fernet = get_fernet()
    encrypted = fernet.encrypt(plaintext.encode())
    return f"enc:{encrypted.decode()}"


def decrypt_value(ciphertext: str) -> str:
    """
    Decrypt an encrypted string value.
    
    Args:
        ciphertext: The encrypted string (with 'enc:' prefix)
        
    Returns:
        Decrypted plaintext string
        
    Raises:
        ValueError: If decryption fails
    """
    if not ciphertext:
        return ciphertext
    
    # Handle non-encrypted values (backwards compatibility)
    if not ciphertext.startswith('enc:'):
        return ciphertext
    
    try:
        fernet = get_fernet()
        encrypted_data = ciphertext[4:]  # Remove 'enc:' prefix
        decrypted = fernet.decrypt(encrypted_data.encode())
        return decrypted.decode()
    except InvalidToken:
        raise ValueError("Failed to decrypt value - invalid token or key")


def encrypt_field(value: Optional[str]) -> Optional[str]:
    """Encrypt a field value, handling None."""
    if value is None:
        return None
    return encrypt_value(value)


def decrypt_field(value: Optional[str]) -> Optional[str]:
    """Decrypt a field value, handling None."""
    if value is None:
        return None
    try:
        return decrypt_value(value)
    except ValueError:
        # Return original value if decryption fails (might be legacy unencrypted data)
        return value


def is_encrypted(value: str) -> bool:
    """Check if a value is encrypted."""
    return value and value.startswith('enc:')


def migrate_to_encrypted(plaintext: str) -> str:
    """
    Migrate a plaintext value to encrypted.
    Safe to call on already-encrypted values.
    """
    if not plaintext:
        return plaintext
    if is_encrypted(plaintext):
        return plaintext
    return encrypt_value(plaintext)


# Convenience class for encrypted fields in SQLAlchemy
class EncryptedString:
    """
    Descriptor for transparently encrypting/decrypting string fields.
    
    Usage in model:
        class User(Base):
            _api_key = Column('api_key', Text)
            api_key = EncryptedString('_api_key')
    """
    
    def __init__(self, column_name: str):
        self.column_name = column_name
    
    def __get__(self, obj, objtype=None):
        if obj is None:
            return self
        value = getattr(obj, self.column_name, None)
        return decrypt_field(value)
    
    def __set__(self, obj, value):
        encrypted = encrypt_field(value)
        setattr(obj, self.column_name, encrypted)
