"""
Up Bank API connector.

This module provides functions for interacting with the Up Bank API,
including authentication, retrieving transactions, and syncing data.
"""

import logging
import requests
from datetime import datetime, timedelta
from flask import current_app
from app.extensions import db
from app.models import Account, AccountType, AccountSource, Transaction, TransactionSource

# Configure logging
logger = logging.getLogger(__name__)


class UpBankAPI:
    """Class for interacting with the Up Bank API."""
    
    def __init__(self, token=None):
        """
        Initialize the Up Bank API connector.
        
        Args:
            token (str, optional): Up Bank API token. If not provided,
                                  will use the token from app config.
        """
        self.base_url = "https://api.up.com.au/api/v1"
        self.token = token or current_app.config.get('UP_BANK_API_TOKEN')
        
        if not self.token:
            raise ValueError("Up Bank API token is required")
        
        self.headers = {
            "Authorization": f"Bearer {self.token}",
            "Accept": "application/json"
        }
    
    def ping(self):
        """
        Test the API connection.
        
        Returns:
            bool: True if connection successful, False otherwise
        """
        try:
            response = requests.get(f"{self.base_url}/util/ping", headers=self.headers)
            return response.status_code == 200
        except Exception as e:
            logger.error(f"Error pinging Up Bank API: {str(e)}")
            return False
    
    def get_accounts(self):
        """
        Retrieve accounts from Up Bank.
        
        Returns:
            list: List of account data dictionaries
        """
        try:
            response = requests.get(f"{self.base_url}/accounts", headers=self.headers)
            
            if response.status_code != 200:
                logger.error(f"Error retrieving accounts: {response.status_code}, {response.text}")
                return []
            
            return response.json().get('data', [])
        except Exception as e:
            logger.error(f"Error retrieving accounts: {str(e)}")
            return []
    
    def get_transactions(self, account_id=None, since=None, until=None, category=None, page_size=100):
        """
        Retrieve transactions from Up Bank.
        
        Args:
            account_id (str, optional): Filter by account ID
            since (datetime, optional): Filter transactions since this date
            until (datetime, optional): Filter transactions until this date
            category (str, optional): Filter by category
            page_size (int, optional): Number of transactions per page
            
        Returns:
            list: List of transaction data dictionaries
        """
        try:
            url = f"{self.base_url}/transactions"
            params = {"page[size]": page_size}
            
            # Add filters if provided
            filter_params = {}
            
            if account_id:
                filter_params["accountId"] = account_id
            
            if since:
                filter_params["since"] = since.isoformat()
            
            if until:
                filter_params["until"] = until.isoformat()
            
            if category:
                filter_params["category"] = category
            
            # Add filter params to request params
            if filter_params:
                for key, value in filter_params.items():
                    params[f"filter[{key}]"] = value
            
            # Handle pagination
            all_transactions = []
            next_page_url = url
            
            while next_page_url:
                # If it's not the first page, use the full URL
                if next_page_url != url:
                    response = requests.get(next_page_url, headers=self.headers)
                else:
                    response = requests.get(url, params=params, headers=self.headers)
                
                if response.status_code != 200:
                    logger.error(f"Error retrieving transactions: {response.status_code}, {response.text}")
                    break
                
                data = response.json()
                transactions = data.get('data', [])
                all_transactions.extend(transactions)
                
                # Get the next page URL if it exists
                next_page_url = data.get('links', {}).get('next')
            
            return all_transactions
        except Exception as e:
            logger.error(f"Error retrieving transactions: {str(e)}")
            return []
    
    def get_categories(self):
        """
        Retrieve categories from Up Bank.
        
        Returns:
            list: List of category data dictionaries
        """
        try:
            response = requests.get(f"{self.base_url}/categories", headers=self.headers)
            
            if response.status_code != 200:
                logger.error(f"Error retrieving categories: {response.status_code}, {response.text}")
                return []
            
            return response.json().get('data', [])
        except Exception as e:
            logger.error(f"Error retrieving categories: {str(e)}")
            return []
    
    def sync_accounts(self, user_id):
        """
        Sync accounts from Up Bank to the database.
        
        Args:
            user_id (int): User ID to associate the accounts with
            
        Returns:
            tuple: (num_created, num_updated) - Count of created and updated accounts
        """
        accounts_data = self.get_accounts()
        
        if not accounts_data:
            logger.warning("No accounts retrieved from Up Bank")
            return 0, 0
        
        num_created = 0
        num_updated = 0
        
        for account_data in accounts_data:
            # Extract account details
            account_id = account_data.get('id')
            account_type_str = account_data.get('attributes', {}).get('accountType', '').upper()
            display_name = account_data.get('attributes', {}).get('displayName', 'Up Account')
            balance_value = account_data.get('attributes', {}).get('balance', {}).get('value', '0')
            currency_code = account_data.get('attributes', {}).get('balance', {}).get('currencyCode', 'AUD')
            
            # Convert string balance to float
            try:
                balance = float(balance_value)
            except (ValueError, TypeError):
                balance = 0.0
            
            # Map Up Bank account type to our enum
            account_type_mapping = {
                'SAVER': AccountType.SAVINGS,
                'TRANSACTIONAL': AccountType.CHECKING,
                # Add more mappings as needed
            }
            account_type = account_type_mapping.get(account_type_str, AccountType.CHECKING)
            
            # Check if account already exists
            account = Account.query.filter_by(
                external_id=account_id,
                user_id=user_id
            ).first()
            
            if account:
                # Update existing account
                account.name = display_name
                account.type = account_type
                account.balance = balance
                account.currency = currency_code
                account.updated_at = datetime.utcnow()
                account.last_synced = datetime.utcnow()
                db.session.commit()
                num_updated += 1
            else:
                # Create new account
                account = Account(
                    external_id=account_id,
                    name=display_name,
                    type=account_type,
                    source=AccountSource.UP_BANK,
                    balance=balance,
                    currency=currency_code,
                    user_id=user_id,
                    last_synced=datetime.utcnow()
                )
                db.session.add(account)
                db.session.commit()
                num_created += 1
        
        return num_created, num_updated
    
    def sync_transactions(self, user_id, days_back=30):
        """
        Sync transactions from Up Bank to the database.
        
        Args:
            user_id (int): User ID to associate the transactions with
            days_back (int, optional): Number of days of history to sync
            
        Returns:
            tuple: (num_created, num_updated) - Count of created and updated transactions
        """
        # Get all accounts for this user
        accounts = Account.query.filter_by(
            user_id=user_id,
            source=AccountSource.UP_BANK
        ).all()
        
        if not accounts:
            logger.warning("No Up Bank accounts found for user")
            return 0, 0
        
        num_created = 0
        num_updated = 0
        
        # Calculate the date range
        since_date = datetime.now() - timedelta(days=days_back)
        
        # Get transactions for each account
        for account in accounts:
            transactions_data = self.get_transactions(
                account_id=account.external_id,
                since=since_date
            )
            
            for tx_data in transactions_data:
                # Extract transaction details
                tx_id = tx_data.get('id')
                status = tx_data.get('attributes', {}).get('status')
                
                # Skip pending transactions if desired
                if status == 'PENDING':
                    continue
                
                description = tx_data.get('attributes', {}).get('description', '')
                message = tx_data.get('attributes', {}).get('message', '')
                
                # Combine description and message if both exist
                if message and message != description:
                    full_description = f"{description} - {message}"
                else:
                    full_description = description
                
                # Get amount details
                amount_value = tx_data.get('attributes', {}).get('amount', {}).get('value', '0')
                created_at_str = tx_data.get('attributes', {}).get('createdAt')
                settled_at_str = tx_data.get('attributes', {}).get('settledAt')
                
                # Convert string amount to float
                try:
                    amount = float(amount_value)
                except (ValueError, TypeError):
                    amount = 0.0
                
                # Parse dates
                try:
                    created_at = datetime.fromisoformat(created_at_str.replace('Z', '+00:00'))
                    transaction_date = created_at.date()
                except (ValueError, TypeError, AttributeError):
                    created_at = datetime.utcnow()
                    transaction_date = created_at.date()
                
                try:
                    if settled_at_str:
                        settled_at = datetime.fromisoformat(settled_at_str.replace('Z', '+00:00'))
                    else:
                        settled_at = None
                except (ValueError, TypeError, AttributeError):
                    settled_at = None
                
                # Get category if available
                category_id = None
                category_data = tx_data.get('relationships', {}).get('category', {}).get('data')
                if category_data:
                    category_id = category_data.get('id')
                
                # Check if transaction already exists
                transaction = Transaction.query.filter_by(
                    external_id=tx_id,
                    user_id=user_id
                ).first()
                
                if transaction:
                    # Update existing transaction
                    transaction.amount = amount
                    transaction.description = full_description
                    transaction.updated_at = datetime.utcnow()
                    if settled_at:
                        transaction.date = settled_at.date()
                    db.session.commit()
                    num_updated += 1
                else:
                    # Create new transaction
                    transaction = Transaction(
                        external_id=tx_id,
                        date=transaction_date,
                        amount=amount,
                        description=full_description,
                        source=TransactionSource.UP_BANK,
                        user_id=user_id,
                        account_id=account.id,
                        category_id=None  # We'll handle categories separately
                    )
                    db.session.add(transaction)
                    db.session.commit()
                    num_created += 1
            
            # Update account last synced timestamp
            account.last_synced = datetime.utcnow()
            db.session.commit()
        
        return num_created, num_updated


# Helper function to get an API instance
def get_up_bank_api(token=None):
    """
    Get an instance of the Up Bank API connector.
    
    Args:
        token (str, optional): Up Bank API token
        
    Returns:
        UpBankAPI: An initialized API connector
    """
    return UpBankAPI(token=token)
