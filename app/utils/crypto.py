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


def generate_encryption_key():
    """
    Generate a new encryption key for sensitive data.
    
    Returns:
        bytes: A new random encryption key
    """
    return Fernet.generate_key()


def _get_encryption_key():
    """
    Get the encryption key from environment or generate if needed.
    
    The key is looked for in this order:
    1. ENCRYPTION_KEY environment variable
    2. An encryption key file (.encryption_key)
    3. Derived from the application secret key (fallback)
    
    Returns:
        bytes: The encryption key
    """
    # Try to get from environment variable first (most secure)
    env_key = os.environ.get('ENCRYPTION_KEY')
    if env_key:
        try:
            # Ensure it's a valid Fernet key (32 url-safe base64-encoded bytes)
            key = base64.urlsafe_b64decode(env_key + '=' * (-len(env_key) % 4))
            if len(key) == 32:
                return env_key.encode('utf-8')
        except Exception:
            logger.warning("Invalid ENCRYPTION_KEY in environment, falling back")
    
    # Try to get from a key file
    key_file = os.path.join(os.path.dirname(os.path.dirname(__file__)), '.encryption_key')
    if os.path.exists(key_file):
        try:
            with open(key_file, 'rb') as f:
                key_data = f.read().strip()
                # Validate the key
                Fernet(key_data)
                return key_data
        except Exception:
            logger.warning("Invalid encryption key in file, falling back")
    
    # Final fallback: derive from app secret key
    # This is less secure but ensures the application can still function
    secret_key = current_app.config.get('SECRET_KEY', 'default-secret-key')
    if isinstance(secret_key, str):
        secret_key = secret_key.encode('utf-8')
    
    # Use a fixed salt for deterministic key derivation
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
    
    # Log that we're using the fallback method
    logger.warning("Using derived encryption key. For better security, set ENCRYPTION_KEY environment variable.")
    
    return key


def store_encryption_key_to_file(key=None):
    """
    Store a new encryption key to a file for development use.
    
    Args:
        key (bytes, optional): The key to store, or generate a new one if None
        
    Returns:
        bytes: The encryption key
    """
    if key is None:
        key = generate_encryption_key()
    
    key_file = os.path.join(os.path.dirname(os.path.dirname(__file__)), '.encryption_key')
    
    # Write the key to file
    with open(key_file, 'wb') as f:
        f.write(key)
    
    # Set restrictive permissions
    try:
        os.chmod(key_file, 0o600)  # Only owner can read/write
    except Exception:
        logger.warning("Could not set permissions on key file")
    
    return key


def encrypt_token(token, use_env_key=True):
    """
    Encrypt a sensitive token.
    
    Args:
        token (str): The token to encrypt
        use_env_key (bool): Whether to use the environment key
    
    Returns:
        str: The encrypted token (or None if encryption fails)
    """
    if not token:
        return None
    
    try:
        # Get the encryption key
        key = _get_encryption_key()
        
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


def decrypt_token(encrypted_token, use_env_key=True):
    """
    Decrypt an encrypted token.
    
    Args:
        encrypted_token (str): The encrypted token
        use_env_key (bool): Whether to use the environment key
    
    Returns:
        str: The decrypted token (or None if decryption fails)
    """
    if not encrypted_token:
        return None
    
    try:
        # Get the encryption key
        key = _get_encryption_key()
        
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


# Add a helper to initialize the encryption key
def init_encryption_key():
    """
    Initialize the encryption key during application startup.
    
    This should be called during app initialization to ensure
    a valid encryption key is available.
    """
    # If environment variable is set, use that
    if os.environ.get('ENCRYPTION_KEY'):
        logger.info("Using encryption key from environment variable")
        return
    
    # If key file exists, use that
    key_file = os.path.join(os.path.dirname(os.path.dirname(__file__)), '.encryption_key')
    if os.path.exists(key_file):
        logger.info("Using encryption key from file")
        return
    
    # Otherwise, generate and store a new key
    logger.info("Generating new encryption key and storing to file")
    store_encryption_key_to_file()
