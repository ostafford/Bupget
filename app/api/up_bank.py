"""
Up Bank API connector.

This module provides functions for interacting with the Up Bank API,
focusing on authentication and basic API access.
"""

import logging
import requests
from flask import current_app

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
            
            if response.status_code == 200:
                logger.info("Successfully connected to Up Bank API")
                return True
            else:
                logger.error(f"Failed to connect to Up Bank API: {response.status_code}, {response.text}")
                return False
        except Exception as e:
            logger.error(f"Error pinging Up Bank API: {str(e)}")
            return False
    
    def validate_token(self):
        """
        Validate the Up Bank API token.
        
        Returns:
            dict: Response containing validation status
        """
        try:
            # The ping endpoint is useful for validating tokens
            response = requests.get(f"{self.base_url}/util/ping", headers=self.headers)
            
            if response.status_code == 200:
                return {
                    "valid": True,
                    "message": "Token is valid"
                }
            elif response.status_code == 401:
                return {
                    "valid": False,
                    "message": "Token is invalid or expired"
                }
            else:
                return {
                    "valid": False,
                    "message": f"Unexpected response from Up Bank API: {response.status_code}"
                }
        except Exception as e:
            logger.error(f"Error validating Up Bank token: {str(e)}")
            return {
                "valid": False,
                "message": f"Error connecting to Up Bank API: {str(e)}"
            }
    
    def handle_response(self, response):
        """
        Helper method to handle API responses.
        
        Args:
            response (requests.Response): The API response
            
        Returns:
            dict: The parsed response data or error information
            
        Raises:
            Exception: If the response contains an error
        """
        if response.status_code >= 200 and response.status_code < 300:
            # Success response
            return response.json()
        elif response.status_code == 401:
            # Authentication error
            logger.error("Authentication failed: Invalid or expired token")
            raise Exception("Authentication failed: Invalid or expired token")
        elif response.status_code == 403:
            # Permission error
            logger.error("Permission denied: Token does not have required permissions")
            raise Exception("Permission denied: Token does not have required permissions")
        elif response.status_code == 429:
            # Rate limit error
            logger.error("Rate limit exceeded: Too many requests")
            raise Exception("Rate limit exceeded: Too many requests")
        else:
            # Other error
            error_message = f"API error: {response.status_code}"
            try:
                error_data = response.json()
                if 'errors' in error_data and error_data['errors']:
                    error_message = f"API error: {error_data['errors'][0].get('detail', 'Unknown error')}"
            except:
                pass
            
            logger.error(error_message)
            raise Exception(error_message)

    def get_accounts(self, account_type=None):
        """
        Retrieve accounts from Up Bank.
        
        Args:
            account_type (str, optional): Filter by account type (TRANSACTIONAL, SAVER)
            
        Returns:
            list: List of account data dictionaries
        """
        try:
            # Build the URL with optional filter
            url = f"{self.base_url}/accounts"
            params = {}
            
            if account_type:
                params["filter[type]"] = account_type
            
            # Make the request
            response = requests.get(url, params=params, headers=self.headers)
            
            if response.status_code != 200:
                logger.error(f"Error retrieving accounts: {response.status_code}, {response.text}")
                return []
            
            # Parse and return the data
            data = response.json()
            return data.get('data', [])
        except Exception as e:
            logger.error(f"Error retrieving accounts: {str(e)}")
            return []
        
    def get_account_by_id(self, account_id):
        """
        Retrieve a specific account by ID.
        
        Args:
            account_id (str): The Up Bank account ID
            
        Returns:
            dict: Account data dictionary or None if not found
        """
        try:
            # Make the request
            response = requests.get(f"{self.base_url}/accounts/{account_id}", headers=self.headers)
            
            if response.status_code != 200:
                logger.error(f"Error retrieving account {account_id}: {response.status_code}, {response.text}")
                return None
            
            # Parse and return the data
            data = response.json()
            return data.get('data')
        except Exception as e:
            logger.error(f"Error retrieving account {account_id}: {str(e)}")
            return None
            
    def get_account_balance(self, account_id):
        """
        Get the balance for a specific account.
        
        Args:
            account_id (str): The Up Bank account ID
            
        Returns:
            dict: Balance information with 'value' and 'currencyCode' or None if error
        """
        account = self.get_account_by_id(account_id)
        
        if not account or 'attributes' not in account:
            return None
        
        return account.get('attributes', {}).get('balance')
            
    def get_all_account_balances(self):
        """
        Get balances for all accounts.
        
        Returns:
            dict: Dictionary mapping account IDs to balance information
        """
        accounts = self.get_accounts()
        balances = {}
        
        for account in accounts:
            account_id = account.get('id')
            if not account_id:
                continue
                
            attributes = account.get('attributes', {})
            balance = attributes.get('balance')
            
            if balance:
                balances[account_id] = balance
        
        return balances


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


# Command line function to test API connection
def test_api_connection(token):
    """
    Test connection to the Up Bank API.
    
    Args:
        token (str): Up Bank API token
        
    Returns:
        bool: True if connection successful, False otherwise
    """
    try:
        api = UpBankAPI(token=token)
        return api.ping()
    except Exception as e:
        logger.error(f"Error testing API connection: {str(e)}")
        return False