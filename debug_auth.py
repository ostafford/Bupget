"""
Debugging script for the Up Bank API authentication process.

This script demonstrates the authentication process step by step
with detailed logging.
"""

import os
import sys
import logging
import base64
import requests
from datetime import datetime

# Configure logging to show everything
logging.basicConfig(level=logging.DEBUG, 
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('auth_debug')

def debug_auth_process(token):
    """Debug the authentication process step by step."""
    logger.info("Starting authentication debugging process")
    
    # Step 1: Check token format
    logger.info("Step 1: Checking token format")
    if not token.startswith("up:yeah:"):
        logger.error("Token does not have the expected format (should start with 'up:yeah:')")
        return False
    
    # Only show first and last few characters of token for security
    visible_token = f"{token[:10]}...{token[-6:]}"
    logger.info(f"Token format looks valid: {visible_token}")
    
    # Step 2: Prepare API request
    logger.info("Step 2: Preparing API request")
    base_url = "https://api.up.com.au/api/v1"
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/json"
    }
    logger.debug(f"Base URL: {base_url}")
    logger.debug(f"Headers: {headers}")
    
    # Step 3: Make the request
    logger.info("Step 3: Making request to ping endpoint")
    try:
        response = requests.get(f"{base_url}/util/ping", headers=headers)
        logger.debug(f"Response status code: {response.status_code}")
        logger.debug(f"Response headers: {response.headers}")
        logger.debug(f"Response body: {response.text}")
        
        if response.status_code == 200:
            logger.info("Successfully authenticated with Up Bank API")
            result = True
        else:
            logger.error(f"Authentication failed: {response.status_code}")
            result = False
    except Exception as e:
        logger.error(f"Error making request: {str(e)}")
        result = False
    
    # Step 4: Demonstrate token encryption (without storing)
    logger.info("Step 4: Demonstrating token encryption")
    try:
        # This is a simplified version of the actual encryption code
        # It's just for demonstration and doesn't store anything
        from cryptography.fernet import Fernet
        from cryptography.hazmat.primitives import hashes
        from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
        
        # Use a demo secret key
        secret_key = b'demo-secret-key-for-debugging'
        salt = b'demo-salt-for-debugging'
        
        # Derive a key
        logger.debug("Deriving encryption key")
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000
        )
        key = base64.urlsafe_b64encode(kdf.derive(secret_key))
        
        # Create cipher
        logger.debug("Creating Fernet cipher with derived key")
        cipher = Fernet(key)
        
        # Encrypt token
        logger.debug("Encrypting token")
        token_bytes = token.encode('utf-8')
        encrypted_token = cipher.encrypt(token_bytes)
        encrypted_token_str = encrypted_token.decode('utf-8')
        
        # Show what would be stored (first few chars only)
        logger.info(f"Encrypted token (first 20 chars): {encrypted_token_str[:20]}...")
        
        # Decrypt token to verify
        logger.debug("Decrypting token to verify")
        decrypted_token_bytes = cipher.decrypt(encrypted_token)
        decrypted_token = decrypted_token_bytes.decode('utf-8')
        
        # Verify decryption worked
        if decrypted_token == token:
            logger.info("Encryption/decryption verification successful")
        else:
            logger.error("Encryption/decryption verification failed")
    except Exception as e:
        logger.error(f"Error during encryption demo: {str(e)}")
    
    return result

if __name__ == "__main__":
    # Get token from command line argument or environment variable
    if len(sys.argv) > 1:
        token = sys.argv[1]
    else:
        token = os.environ.get('UP_BANK_TOKEN')
    
    if not token:
        print("Please provide an Up Bank token as argument or set UP_BANK_TOKEN environment variable")
        sys.exit(1)
    
    print("Starting authentication debugging...")
    print("(Check the logs for detailed information)")
    result = debug_auth_process(token)
    
    if result:
        print("✅ Authentication successful")
    else:
        print("❌ Authentication failed")
