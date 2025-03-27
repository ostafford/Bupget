"""
Cryptography utilities.

This module provides functions for securely encrypting and decrypting
sensitive data like API tokens.
"""

import base64
import logging
import os
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from flask import current_app

# Configure logging
logger = logging.getLogger(__name__)


def _get_encryption_key(app_secret_key=None):
    """
    Get or generate the encryption key for sensitive data.
    
    Args:
        app_secret_key (str, optional): The application secret key
                                        If not provided, will use the key from app config
    
    Returns:
        bytes: The encryption key
    """
    # Use the app's secret key or the provided one
    secret_key = app_secret_key or current_app.config.get('SECRET_KEY', 'default-secret-key')
    
    # Convert string key to bytes if necessary
    if isinstance(secret_key, str):
        secret_key = secret_key.encode('utf-8')
    
    # Use a fixed salt for deterministic key derivation
    # In a production system, this should be a securely stored value
    salt = b'budget-app-fixed-salt'
    
    # Derive a key using PBKDF2
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=100000
    )
    
    # Generate the key
    key = base64.urlsafe_b64encode(kdf.derive(secret_key))
    
    return key


def encrypt_token(token, app_secret_key=None):
    """
    Encrypt a sensitive token.
    
    Args:
        token (str): The token to encrypt
        app_secret_key (str, optional): The application secret key
    
    Returns:
        str: The encrypted token (or None if encryption fails)
    """
    if not token:
        return None
    
    try:
        # Get the encryption key
        key = _get_encryption_key(app_secret_key)
        
        # Create a Fernet cipher
        cipher = Fernet(key)
        
        # Convert token to bytes if necessary
        if isinstance(token, str):
            token = token.encode('utf-8')
        
        # Encrypt the token
        encrypted_token = cipher.encrypt(token)
        
        # Convert to string for storage
        return encrypted_token.decode('utf-8')
    except Exception as e:
        logger.error(f"Error encrypting token: {str(e)}")
        return None


def decrypt_token(encrypted_token, app_secret_key=None):
    """
    Decrypt an encrypted token.
    
    Args:
        encrypted_token (str): The encrypted token
        app_secret_key (str, optional): The application secret key
    
    Returns:
        str: The decrypted token (or None if decryption fails)
    """
    if not encrypted_token:
        return None
    
    try:
        # Get the encryption key
        key = _get_encryption_key(app_secret_key)
        
        # Create a Fernet cipher
        cipher = Fernet(key)
        
        # Convert encrypted token to bytes if necessary
        if isinstance(encrypted_token, str):
            encrypted_token = encrypted_token.encode('utf-8')
        
        # Decrypt the token
        decrypted_token = cipher.decrypt(encrypted_token)
        
        # Convert back to string
        return decrypted_token.decode('utf-8')
    except Exception as e:
        logger.error(f"Error decrypting token: {str(e)}")
        return None
