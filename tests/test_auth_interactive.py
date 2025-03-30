#!/usr/bin/env python
"""
Interactive Authentication Test Script.

This script walks you through the authentication process with Up Bank
step by step, with visual feedback at each stage.
"""

import os
import sys
import time
import base64
from getpass import getpass
from datetime import datetime

try:
    import requests
    from cryptography.fernet import Fernet
    from cryptography.hazmat.primitives import hashes
    from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
    from app.api.up_bank import UpBankAPI
    from app.utils.crypto import encrypt_token, decrypt_token
except ImportError:
    print("Error: Required libraries not found.")
    print("Make sure you're running this script from the project root and the virtual environment is activated.")
    sys.exit(1)

def clear_screen():
    """Clear the terminal screen."""
    os.system('cls' if os.name == 'nt' else 'clear')

def print_header(text):
    """Print a formatted header."""
    width = 80
    print("\n" + "=" * width)
    print(text.center(width))
    print("=" * width + "\n")

def print_step(step_num, title):
    """Print a formatted step header."""
    print(f"\n----- Step {step_num}: {title} -----\n")

def wait_for_user():
    """Wait for user to press Enter to continue."""
    input("\nPress Enter to continue...")

def test_token_format(token):
    """Test if the token has the correct format."""
    if not token.startswith("up:yeah:"):
        print("❌ Token format is invalid. Up Bank tokens should start with 'up:yeah:'")
        return False
    print("✅ Token format looks valid")
    return True

def test_token_auth(token):
    """Test token authentication with Up Bank API."""
    print("📡 Connecting to Up Bank API...")
    try:
        api = UpBankAPI(token=token)
        result = api.ping()
        
        if result:
            print("✅ Successfully authenticated with Up Bank API")
            return True
        else:
            print("❌ Authentication failed")
            return False
    except Exception as e:
        print(f"❌ Error during authentication: {str(e)}")
        return False

def demonstrate_encryption(token, encryption_key=None):
    """Demonstrate token encryption and decryption."""
    print("🔒 Demonstrating token encryption process...")
    
    # Try to get encryption key from file or environment
    if not encryption_key:
        # Try to read from file
        key_file = os.path.join(os.path.dirname(__file__), '.encryption_key')
        if os.path.exists(key_file):
            with open(key_file, 'rb') as f:
                encryption_key = f.read().strip()
        else:
            # Try environment
            encryption_key = os.environ.get('ENCRYPTION_KEY')
            if encryption_key:
                encryption_key = encryption_key.encode('utf-8')
    
    if not encryption_key:
        print("⚠️  No encryption key found. Using a temporary one for demonstration.")
        # Generate a temporary key for demo
        encryption_key = Fernet.generate_key()
    
    # Use our encryption function
    print("\nEncrypting token...")
    encrypted = encrypt_token(token)
    
    print(f"Original token (first 10 chars): {token[:10]}...")
    print(f"Encrypted token (first 20 chars): {encrypted[:20]}...")
    
    # Decrypt to verify
    print("\nDecrypting token...")
    decrypted = decrypt_token(encrypted)
    
    # Verify
    if decrypted == token:
        print("✅ Decryption successful - token recovered correctly")
        return True
    else:
        print("❌ Decryption failed - tokens don't match")
        return False

def simulate_database_storage(token):
    """Simulate storing the token in the database."""
    print("💾 Simulating database storage of encrypted token...")
    
    # Encrypt the token
    encrypted_token = encrypt_token(token)
    
    # Show how it would be stored
    print("\nIn the database, we would store:")
    print(f"| user_id | up_bank_token                      | up_bank_token_added_at |")
    print(f"| ------- | ---------------------------------- | --------------------- |")
    print(f"| 1       | {encrypted_token[:30]}... | {datetime.now()}  |")
    
    return encrypted_token

def simulate_api_request(encrypted_token):
    """Simulate making an API request with the stored token."""
    print("🔄 Simulating API request to Up Bank...")
    
    # Decrypt the token
    token = decrypt_token(encrypted_token)
    print("1. Retrieve encrypted token from database")
    print("2. Decrypt token for use")
    
    # Show how we would use it
    print(f"3. Create API request with Authorization header:")
    print(f"   Authorization: Bearer {token[:10]}...")
    
    # Make actual request to demonstrate
    try:
        api = UpBankAPI(token=token)
        result = api.ping()
        
        if result:
            print("4. ✅ API request successful")
            return True
        else:
            print("4. ❌ API request failed")
            return False
    except Exception as e:
        print(f"4. ❌ Error during API request: {str(e)}")
        return False

def run_interactive_test():
    """Run the interactive test."""
    clear_screen()
    print_header("Up Bank API Authentication Interactive Test")
    
    print("""
This script will walk you through the authentication process with Up Bank
step by step, showing you how the system handles your API token securely.
    """)
    
    wait_for_user()
    
    # Step 1: Get token
    print_step(1, "Enter Your Up Bank Token")
    print("You can get a token from the Up Bank developer portal: https://developer.up.com.au/")
    print("Your token will not be stored permanently and will only be used for this test.")
    print("Note: The token input is masked for security.")
    
    token = getpass("\nEnter your Up Bank token: ")
    
    # Step 2: Validate token format
    print_step(2, "Validating Token Format")
    if not test_token_format(token):
        print("\nThe token format doesn't look right. Do you want to continue anyway?")
        choice = input("Continue? (y/n): ")
        if choice.lower() != 'y':
            print("Test aborted.")
            return
    
    wait_for_user()
    
    # Step 3: Test authentication
    print_step(3, "Testing Authentication with Up Bank")
    auth_success = test_token_auth(token)
    
    if not auth_success:
        print("\nAuthentication failed. Do you want to continue with the rest of the test anyway?")
        choice = input("Continue? (y/n): ")
        if choice.lower() != 'y':
            print("Test aborted.")
            return
    
    wait_for_user()
    
    # Step 4: Demonstrate encryption
    print_step(4, "Token Encryption")
    encryption_success = demonstrate_encryption(token)
    
    if not encryption_success:
        print("\nEncryption demonstration had issues. This might indicate a problem with the encryption setup.")
    
    wait_for_user()
    
    # Step 5: Simulate database storage
    print_step(5, "Database Storage")
    encrypted_token = simulate_database_storage(token)
    
    wait_for_user()
    
    # Step 6: Simulate API request
    print_step(6, "Using the Stored Token")
    api_success = simulate_api_request(encrypted_token)
    
    # Final summary
    print_step(7, "Test Summary")
    print("Token Format Test:", "✅ Passed" if test_token_format(token) else "❌ Failed")
    print("Authentication Test:", "✅ Passed" if auth_success else "❌ Failed")
    print("Encryption Test:", "✅ Passed" if encryption_success else "❌ Failed")
    print("API Usage Test:", "✅ Passed" if api_success else "❌ Failed")
    
    print("\nTest completed!")
    print("""
Key points to remember:
1. Your token is encrypted before storage
2. The token is only decrypted when needed for API calls
3. The encryption key is stored separately from the database
4. Token rotation helps ensure long-term security
    """)

if __name__ == "__main__":
    run_interactive_test()
