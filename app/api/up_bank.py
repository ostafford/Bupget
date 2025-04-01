"""
Up Bank API connector.

This module provides functions for interacting with the Up Bank API,
focusing on authentication and basic API access.
"""

import logging
import requests
import json
from requests.exceptions import RequestException, ConnectionError, Timeout, HTTPError
from flask import current_app

from app.utils.retry import retry, handle_api_exception, APIErrorResponse

# Configure logging
logger = logging.getLogger(__name__)


class UpBankError(Exception):
    """Base exception for Up Bank API errors."""
    pass


class UpBankAuthError(UpBankError):
    """Exception for authentication errors."""
    pass


class UpBankAPIError(UpBankError):
    """Exception for API errors."""
    def __init__(self, message, status_code=None, response=None):
        self.status_code = status_code
        self.response = response
        super().__init__(message)


class UpBankRateLimitError(UpBankAPIError):
    """Exception for rate limit errors."""
    def __init__(self, message, retry_after=None, **kwargs):
        self.retry_after = retry_after
        super().__init__(message, **kwargs)


class UpBankConnectionError(UpBankError):
    """Exception for connection errors."""
    pass


class UpBankAPI:
    """Class for interacting with the Up Bank API."""
    
    # Maximum number of attempts for API calls
    MAX_RETRIES = 3
    
    # Default timeout for API calls (in seconds)
    DEFAULT_TIMEOUT = 10
    
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
            "Accept": "application/json",
            "User-Agent": "Budget App/1.0"
        }
    
    def _make_request(self, method, endpoint, params=None, data=None, timeout=None):
        """
        Make an HTTP request to the Up Bank API with error handling.
        
        Args:
            method (str): HTTP method (get, post, etc.)
            endpoint (str): API endpoint (without base URL)
            params (dict, optional): Query parameters
            data (dict, optional): Request body data
            timeout (int, optional): Request timeout in seconds
            
        Returns:
            dict: API response parsed as JSON
            
        Raises:
            UpBankAuthError: If authentication fails
            UpBankRateLimitError: If rate limits are exceeded
            UpBankAPIError: If the API returns an error
            UpBankConnectionError: If there's a network error
        """
        # Ensure the endpoint doesn't start with a slash
        if endpoint.startswith('/'):
            endpoint = endpoint[1:]
        
        # Build the full URL
        url = f"{self.base_url}/{endpoint}"
        
        # Use default timeout if not specified
        if timeout is None:
            timeout = self.DEFAULT_TIMEOUT
        
        # Convert data to JSON if provided
        json_data = None
        if data:
            json_data = json.dumps(data)
        
        try:
            # Make the request
            response = requests.request(
                method=method.upper(),
                url=url,
                params=params,
                headers=self.headers,
                json=data,
                timeout=timeout
            )
            
            # Log the request (but not the full headers to avoid logging the token)
            log_headers = {k: v for k, v in self.headers.items() if k != 'Authorization'}
            logger.debug(f"API Request: {method.upper()} {url}")
            logger.debug(f"Headers: {log_headers}")
            
            if params:
                logger.debug(f"Params: {params}")
            
            # Check for error responses
            if response.status_code >= 400:
                self._handle_error_response(response)
                
            # Parse and return the successful response
            return response.json()
            
        except json.JSONDecodeError as e:
            # Handle invalid JSON response
            logger.error(f"Invalid JSON response from Up Bank API: {str(e)}")
            raise UpBankAPIError(f"Invalid response format: {str(e)}")
            
        except requests.exceptions.Timeout as e:
            # Handle timeout
            logger.error(f"Timeout connecting to Up Bank API: {str(e)}")
            raise UpBankConnectionError(f"Connection timeout: {str(e)}")
            
        except requests.exceptions.ConnectionError as e:
            # Handle connection errors
            logger.error(f"Error connecting to Up Bank API: {str(e)}")
            raise UpBankConnectionError(f"Connection error: {str(e)}")
            
        except Exception as e:
            # Handle any other exceptions
            logger.error(f"Unexpected error in Up Bank API request: {str(e)}")
            raise UpBankError(f"Unexpected error: {str(e)}")
    
    def _handle_error_response(self, response):
        """
        Handle error responses from the Up Bank API.
        
        Args:
            response (Response): The error response
            
        Raises:
            UpBankAuthError: For authentication errors (401)
            UpBankRateLimitError: For rate limit errors (429)
            UpBankAPIError: For other API errors
        """
        status_code = response.status_code
        error_message = f"API error: {status_code}"
        
        # Try to get error details from response
        try:
            error_data = response.json()
            if 'errors' in error_data and error_data['errors']:
                error_detail = error_data['errors'][0].get('detail', 'Unknown error')
                error_message = f"API error ({status_code}): {error_detail}"
        except:
            # If we can't parse the JSON, use the status code and text
            error_message = f"API error ({status_code}): {response.text}"
        
        # Log the error
        logger.error(error_message)
        
        # Raise appropriate exception based on status code
        if status_code == 401:
            raise UpBankAuthError("Authentication failed: Invalid or expired token")
            
        elif status_code == 403:
            raise UpBankAuthError("Permission denied: Token does not have required permissions")
        
        elif status_code == 404:
            raise UpBankAPIError(f"Resource not found: {error_message}", status_code=status_code, response=response)
            
        elif status_code == 429:
            # Get retry-after header if available
            retry_after = None
            if 'Retry-After' in response.headers:
                try:
                    retry_after = int(response.headers['Retry-After'])
                except (ValueError, TypeError):
                    pass
                    
            raise UpBankRateLimitError(
                "Rate limit exceeded: Too many requests",
                retry_after=retry_after,
                status_code=status_code,
                response=response
            )
            
        else:
            raise UpBankAPIError(error_message, status_code=status_code, response=response)
    
    @retry(
        exceptions=[ConnectionError, Timeout, UpBankConnectionError, UpBankRateLimitError, UpBankError],
        tries=MAX_RETRIES,
        delay=2,
        backoff=2,
        jitter=0.1
    )
    def ping(self):
        """
        Test the API connection.
        
        Returns:
            bool: True if connection successful, False otherwise
        """
        try:
            self._make_request('get', 'util/ping')
            logger.info("Successfully connected to Up Bank API")
            return True
        except UpBankAuthError:
            # Don't retry authentication errors
            logger.error("Authentication failed with Up Bank API")
            return False
        except Exception as e:
            # Log the error, but re-raise for the retry decorator
            logger.error(f"Error pinging Up Bank API: {str(e)}")
            raise
    
    @retry(
        exceptions=[ConnectionError, Timeout, UpBankConnectionError, UpBankRateLimitError],
        tries=MAX_RETRIES,
        delay=2,
        backoff=2,
        jitter=0.1
    )
    def validate_token(self):
        """
        Validate the Up Bank API token.
        
        Returns:
            dict: Response containing validation status
        """
        try:
            # Use the ping endpoint to validate the token
            self._make_request('get', 'util/ping')
            
            return {
                "valid": True,
                "message": "Token is valid"
            }
        except UpBankAuthError:
            return {
                "valid": False,
                "message": "Token is invalid or expired"
            }
        except Exception as e:
            # Create a standardized error response
            error_response = handle_api_exception(
                e, 
                "Up Bank API", 
                "validate_token"
            )
            return {
                "valid": False,
                "message": error_response.message
            }

    @retry(
        exceptions=[ConnectionError, Timeout, UpBankConnectionError, UpBankRateLimitError],
        tries=MAX_RETRIES,
        delay=2,
        backoff=2,
        jitter=0.1
    )
    def get_accounts(self, account_type=None):
        """
        Retrieve accounts from Up Bank.
        
        Args:
            account_type (str, optional): Filter by account type (TRANSACTIONAL, SAVER)
            
        Returns:
            list: List of account data dictionaries
        """
        try:
            # Build optional filter parameters
            params = {}
            if account_type:
                params["filter[type]"] = account_type
            
            # Make the request
            response = self._make_request('get', 'accounts', params=params)
            
            # Return the data
            return response.get('data', [])
        except Exception as e:
            # Log the error and return empty list (don't raise for retrying)
            logger.error(f"Error retrieving accounts: {str(e)}")
            return []
        
    @retry(
        exceptions=[ConnectionError, Timeout, UpBankConnectionError, UpBankRateLimitError],
        tries=MAX_RETRIES,
        delay=2,
        backoff=2,
        jitter=0.1
    )
    def get_account_by_id(self, account_id):
        """
        Retrieve a specific account by ID.
        
        Args:
            account_id (str): The Up Bank account ID
            
        Returns:
            dict: Account data dictionary or None if not found
        """
        try:
            response = self._make_request('get', f'accounts/{account_id}')
            return response.get('data')
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
    
    @retry(
        exceptions=[ConnectionError, Timeout, UpBankConnectionError, UpBankRateLimitError],
        tries=MAX_RETRIES,
        delay=2,
        backoff=2,
        jitter=0.1
    )
    def get_transaction_by_id(self, transaction_id):
        """
        Retrieve a specific transaction by ID.
        
        Args:
            transaction_id (str): The Up Bank transaction ID
            
        Returns:
            dict: Transaction data dictionary or None if not found
        """
        try:
            response = self._make_request('get', f'transactions/{transaction_id}')
            return response.get('data')
        except Exception as e:
            logger.error(f"Error retrieving transaction {transaction_id}: {str(e)}")
            return None
    
    def sync_transactions(self, user_id, days_back=30):
        """
        Sync transactions from Up Bank for a user.
        
        Args:
            user_id (int): The user ID to sync transactions for
            days_back (int): Number of days to look back for transactions
                
        Returns:
            tuple: (new_transactions_count, updated_transactions_count)
        """
        from datetime import datetime, timedelta
        from app.models import Transaction, TransactionSource, Account
        from app.extensions import db
        
        try:
            # Calculate the date range for transactions
            end_date = datetime.now()
            start_date = end_date - timedelta(days=days_back)
            
            # Format dates for the API
            since_date = start_date.strftime('%Y-%m-%dT00:00:00Z')
            
            # Start with just the endpoint path (no base URL)
            endpoint = f"transactions?filter[since]={since_date}"
            
            created_count = 0
            updated_count = 0
            
            # Get all accounts for this user to map external_id to account_id
            accounts = Account.query.filter_by(user_id=user_id).all()
            account_map = {account.external_id: account.id for account in accounts}
            
            # Track failed transactions for reporting
            failed_transactions = []
            max_failures = 5  # Maximum number of failures to tolerate
            
            # Fetch transactions page by page
            while endpoint:
                logger.info(f"Fetching transactions endpoint: {endpoint}")
                
                try:
                    # Make the API request with retry, using just the endpoint path
                    response = self._make_request('get', endpoint)
                    
                    # Process the data
                    transactions = response.get('data', [])
                    
                    # Process each transaction
                    for tx_data in transactions:
                        tx_id = tx_data.get('id')
                        if not tx_id:
                            continue
                        
                        try:
                            # Process the transaction
                            result = self._process_transaction(tx_data, user_id, account_map)
                            
                            if result == "created":
                                created_count += 1
                            elif result == "updated":
                                updated_count += 1
                        except Exception as tx_e:
                            # Log the error and continue with next transaction
                            logger.error(f"Error processing transaction {tx_id}: {str(tx_e)}")
                            failed_transactions.append(tx_id)
                            
                            # If too many failures, stop processing
                            if len(failed_transactions) >= max_failures:
                                logger.error(f"Too many transaction processing failures ({len(failed_transactions)}), aborting sync")
                                break
                    
                    # Commit the batch
                    db.session.commit()
                    
                    # Check for pagination
                    links = response.get('links', {})
                    next_url = links.get('next')
                    
                    # If no more pages, stop
                    if not next_url:
                        break
                        
                    # If we've had too many failures, stop
                    if len(failed_transactions) >= max_failures:
                        break
                    
                    # If next_url is a full URL, extract just the path
                    if next_url.startswith('http'):
                        # Extract path from full URL
                        from urllib.parse import urlparse
                        parsed_url = urlparse(next_url)
                        endpoint = parsed_url.path
                        if parsed_url.query:
                            endpoint = f"{endpoint}?{parsed_url.query}"
                        # Remove leading slash if present
                        if endpoint.startswith('/'):
                            endpoint = endpoint[1:]
                    else:
                        # It's already a relative path
                        endpoint = next_url
                        # Remove leading slash if present
                        if endpoint.startswith('/'):
                            endpoint = endpoint[1:]
                        
                except UpBankAPIError as api_e:
                    # Handle specific API errors
                    logger.error(f"API error fetching transactions: {str(api_e)}")
                    
                    # If it's a 404 or other non-retryable error, stop syncing
                    if hasattr(api_e, 'status_code'):
                        if api_e.status_code == 404:
                            logger.error("Encountered 404 error - endpoint does not exist. Stopping sync.")
                            break
                    
                    # For other API errors, don't continue
                    break
                    
                except Exception as page_e:
                    # Log the error and stop
                    logger.error(f"Unexpected error fetching transactions: {str(page_e)}")
                    break
            
            # Report any failures
            if failed_transactions:
                logger.warning(f"Failed to process {len(failed_transactions)} transactions: {failed_transactions}")
            
            return created_count, updated_count
        
        except Exception as e:
            logger.error(f"Error syncing transactions: {str(e)}")
            db.session.rollback()
            return 0, 0
    
    def _process_transaction(self, transaction_data, user_id, account_map):
        """
        Process a transaction from Up Bank API.
        
        Args:
            transaction_data (dict): Transaction data from API
            user_id (int): User ID to assign the transaction to
            account_map (dict): Map of external account IDs to internal account IDs
            
        Returns:
            str: "created" if a new transaction was created, "updated" if updated, None if failed
        """
        from datetime import datetime
        from app.models import Transaction, TransactionSource
        from app.extensions import db
        
        # Extract the transaction ID
        tx_id = transaction_data.get('id')
        if not tx_id:
            logger.error("Transaction ID not found in data")
            return None
        
        # Extract transaction details from attributes
        attributes = transaction_data.get('attributes', {})
        
        # Get transaction description
        description = attributes.get('description', 'Unknown transaction')
        
        # Try to get a more meaningful description
        if 'rawText' in attributes and attributes['rawText']:
            description = attributes['rawText']
        
        # Extract date
        created_at = attributes.get('createdAt')
        if not created_at:
            logger.error("Transaction date not found")
            return None
            
        try:
            tx_date = datetime.fromisoformat(created_at.replace('Z', '+00:00')).date()
        except (ValueError, TypeError, AttributeError):
            tx_date = datetime.now().date()
        
        # Extract amount
        amount_data = attributes.get('amount', {})
        value = amount_data.get('value', '0')
        
        try:
            amount = float(value)
        except (ValueError, TypeError):
            amount = 0.0
        
        # Determine account ID
        account_id = None
        relationships = transaction_data.get('relationships', {})
        account_data = relationships.get('account', {}).get('data', {})
        
        if account_data and 'id' in account_data:
            external_account_id = account_data['id']
            account_id = account_map.get(external_account_id)
        
        # Check if transaction already exists
        existing_tx = Transaction.query.filter_by(
            external_id=tx_id,
            user_id=user_id
        ).first()
        
        if existing_tx:
            # Update existing transaction
            existing_tx.description = description
            existing_tx.amount = amount
            existing_tx.date = tx_date
            existing_tx.account_id = account_id
            existing_tx.updated_at = datetime.utcnow()
            
            # If category not already set, try to categorize
            if not existing_tx.category_id:
                from app.services.transaction_service import suggest_category_for_transaction
                category_id = suggest_category_for_transaction(description, user_id)
                if category_id:
                    existing_tx.category_id = category_id
            
            return "updated"
        else:
            # Create new transaction
            # Try to categorize the transaction
            from app.services.transaction_service import suggest_category_for_transaction
            category_id = suggest_category_for_transaction(description, user_id)
            
            new_tx = Transaction(
                external_id=tx_id,
                date=tx_date,
                description=description,
                amount=amount,
                source=TransactionSource.UP_BANK,
                user_id=user_id,
                account_id=account_id,
                category_id=category_id,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )
            
            db.session.add(new_tx)
            return "created"


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