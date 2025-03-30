"""
Test script to verify environment variables loading from .env file.
"""

import os
from dotenv import load_dotenv

# Explicitly load from .env file
print("Attempting to load .env file...")
result = load_dotenv(verbose=True)

if result:
    print("SUCCESS: .env file loaded successfully")
else:
    print("WARNING: .env file not found or empty")

# Check critical environment variables
print("\nChecking environment variables:")
print(f"FLASK_CONFIG: {os.environ.get('FLASK_CONFIG', 'NOT SET')}")
print(f"SECRET_KEY: {os.environ.get('SECRET_KEY', 'NOT SET')}")
print(f"DATABASE_URI: {'SET (Hidden for Security)' if os.environ.get('DATABASE_URI') else 'NOT SET'}")
print(f"UP_BANK_API_TOKEN: {'SET (hidden for security)' if os.environ.get('UP_BANK_API_TOKEN') else 'NOT SET'}")
