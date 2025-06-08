"""
Cryptographic utilities for API key handling and security operations.
"""

import hashlib
import secrets
import base64
from typing import Tuple


def hash_api_key(api_key: str) -> str:
    """
    Hash an API key using SHA-256 for secure storage.
    
    Args:
        api_key: The raw API key to hash
        
    Returns:
        str: The hashed API key as a hex string
    """
    return hashlib.sha256(api_key.encode('utf-8')).hexdigest()


def generate_api_key(length: int = 32) -> Tuple[str, str]:
    """
    Generate a new API key and its hash.
    
    Args:
        length: Length of the API key in bytes (default 32)
        
    Returns:
        Tuple[str, str]: (raw_api_key, hashed_api_key)
    """
    # Generate random bytes and encode as base64
    raw_key_bytes = secrets.token_bytes(length)
    raw_api_key = base64.urlsafe_b64encode(raw_key_bytes).decode('utf-8').rstrip('=')
    
    # Hash the key for storage
    hashed_key = hash_api_key(raw_api_key)
    
    return raw_api_key, hashed_key


def verify_api_key(raw_key: str, hashed_key: str) -> bool:
    """
    Verify an API key against its stored hash.
    
    Args:
        raw_key: The raw API key to verify
        hashed_key: The stored hash to verify against
        
    Returns:
        bool: True if the key matches the hash
    """
    return hash_api_key(raw_key) == hashed_key


def generate_secure_token(length: int = 32) -> str:
    """
    Generate a secure random token for various security purposes.
    
    Args:
        length: Length of the token in bytes
        
    Returns:
        str: URL-safe base64 encoded token
    """
    return base64.urlsafe_b64encode(secrets.token_bytes(length)).decode('utf-8').rstrip('=')


def hash_password(password: str) -> str:
    """
    Hash a password using SHA-256 (note: in production, use bcrypt/scrypt/argon2).
    
    Args:
        password: The plain text password
        
    Returns:
        str: The hashed password
    """
    return hashlib.sha256(password.encode('utf-8')).hexdigest()


def verify_password(password: str, hashed_password: str) -> bool:
    """
    Verify a password against its hash.
    
    Args:
        password: The plain text password
        hashed_password: The stored hash
        
    Returns:
        bool: True if the password matches the hash
    """
    return hash_password(password) == hashed_password 