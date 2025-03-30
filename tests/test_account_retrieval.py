# test_account_retrieval.py

import os
import sys
from app import create_app
from app.api.up_bank import get_up_bank_api
from app.services.bank_service import sync_accounts
from app.models import User

def test_account_retrieval(user_id):
    """
    Test account retrieval from Up Bank.
    
    This script tests:
    1. Connection to Up Bank API
    2. Account retrieval
    3. Account synchronization to database
    
    Args:
        user_id: ID of the user to test with
    """
    app = create_app('development')
    with app.app_context():
        from app.extensions import db
        
        # Find the user
        user = User.query.get(user_id)
        if not user:
            print(f"❌ User with ID {user_id} not found")
            return False
        
        # Get the token
        token = user.get_up_bank_token()
        if not token:
            print("❌ No Up Bank token found for user")
            return False
        
        print("Step 1: Testing API connection...")
        api = get_up_bank_api(token=token)
        connection_result = api.ping()
        
        if connection_result:
            print("✅ Successfully connected to Up Bank API")
        else:
            print("❌ Failed to connect to Up Bank API")
            return False
        
        print("\nStep 2: Retrieving Up Bank accounts...")
        accounts = api.get_accounts()
        
        if not accounts:
            print("❌ No accounts found")
            return False
        
        print(f"✅ Found {len(accounts)} accounts:")
        for i, account in enumerate(accounts):
            account_id = account.get('id', 'Unknown')
            attributes = account.get('attributes', {})
            name = attributes.get('displayName', 'Unknown')
            account_type = attributes.get('accountType', 'Unknown')
            
            balance_data = attributes.get('balance', {})
            balance_value = balance_data.get('value', '0')
            currency = balance_data.get('currencyCode', 'AUD')
            
            print(f"\nAccount {i+1}:")
            print(f"  ID: {account_id}")
            print(f"  Name: {name}")
            print(f"  Type: {account_type}")
            print(f"  Balance: {balance_value} {currency}")
        
        print("\nStep 3: Syncing accounts to database...")
        success, message, count = sync_accounts(user_id)
        
        if success:
            print(f"✅ {message}")
            return True
        else:
            print(f"❌ {message}")
            return False


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python test_account_retrieval.py <user_id>")
        sys.exit(1)
    
    user_id = int(sys.argv[1])
    successful = test_account_retrieval(user_id)
    
    if successful:
        print("\n🎉 Account retrieval test PASSED!")
    else:
        print("\n❌ Account retrieval test FAILED!")
